import json

cells = []

def add_markdown(text):
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": [text]
    })

def add_code(code):
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [line + "\n" for line in code.split("\n")]
    })

add_markdown("# 1. Environment Setup\nClone SAM-3D-Body and install dependencies.")
add_code("""
import os
import sys

# Change this to /content if running in Colab
WORK_DIR = "/kaggle/working"
os.chdir(WORK_DIR)

!rm -rf sam-3d-body
!git clone -q https://github.com/facebookresearch/sam-3d-body.git

os.chdir(f"{WORK_DIR}/sam-3d-body")

!pip install -q \\
    pytorch-lightning pyrender opencv-python-headless yacs scikit-image einops timm dill pandas rich hydra-core hydra-submitit-launcher hydra-colorlog pyrootutils webdataset chump networkx==3.2.1 roma joblib seaborn wandb appdirs appnope ffmpeg cython jsonlines pytest xtcocotools loguru optree fvcore black pycocotools tensorboard huggingface_hub braceexpand \\
    fastapi uvicorn pydantic nest-asyncio python-multipart

!pip install -q git+https://github.com/microsoft/MoGe.git
!pip install -q 'git+https://github.com/facebookresearch/detectron2.git@a1ce2f9' --no-build-isolation --no-deps

# IMPORTANT: Insert your HuggingFace token here if the model requires it (like in your Kaggle run)
!python -c "from huggingface_hub import login; login('YOUR_HUGGINGFACE_TOKEN_HERE')"
""")

add_markdown("# 2. The FastAPI Server (MHR Video Processing)\nProcesses `.webm` videos, runs MHR frame-by-frame, and returns 3D joint coordinates as JSON.")
add_code(r"""
%%writefile server.py
import os
import sys
import io
import re
import threading
import subprocess
import urllib.request
import cv2
import json
import contextlib

import torch
import numpy as np
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import nest_asyncio

import concurrent.futures

# Change this to /content if running in Colab
WORK_DIR = "/kaggle/working"
sys.path.insert(0, f"{WORK_DIR}/sam-3d-body")

import importlib.util
utils_path = f"{WORK_DIR}/sam-3d-body/notebook/utils.py"
spec = importlib.util.spec_from_file_location("sam3d_notebook_utils", utils_path)
sam_utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sam_utils)
setup_sam_3d_body = sam_utils.setup_sam_3d_body

print("[*] Loading SAM-3D-Body (MHR) model on GPU 0...")
estimator_0 = setup_sam_3d_body(hf_repo_id="facebook/sam-3d-body-dinov3")
estimators = [estimator_0]

num_gpus = torch.cuda.device_count()
print(f"[-] Total CUDA GPUs detected: {num_gpus}")
if num_gpus >= 2:
    try:
        print("[*] Loading second SAM-3D-Body estimator on GPU 1 (Dual T4 mode)...")
        torch.cuda.set_device(1)
        estimator_1 = setup_sam_3d_body(hf_repo_id="facebook/sam-3d-body-dinov3")
        estimators.append(estimator_1)
        torch.cuda.set_device(0)
        print("[+] Dual GPU parallel mode enabled! (GPU 0 & GPU 1)")
    except Exception as e:
        print(f"[!] Warning: Could not initialize GPU 1 ({e}). Continuing on GPU 0.")
        torch.cuda.set_device(0)

app = FastAPI(title="SignAvatar MHR Backend")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def process_frame_worker(item):
    idx, img_np, est = item
    try:
        output = est.process_one_image(img_np, inference_type="full")
        if not output or len(output) == 0:
            return idx, None
        
        largest_person = None
        max_area = 0
        for person in output:
            bbox = person["bbox"]
            area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
            if area > max_area:
                max_area = area
                largest_person = person
        return idx, largest_person["pred_joint_coords"].tolist()
    except Exception as err:
        print(f"Error on frame {idx}: {err}")
        return idx, None

@app.post("/api/process-video")
async def process_video(video: UploadFile = File(...)):
    try:
        print(f"\n[-] Received video: {video.filename}")
        vid_path = f"{WORK_DIR}/{video.filename}"
        with open(vid_path, "wb") as f:
            f.write(await video.read())
            
        # 1. Read video and sample ~20-24 frames for rapid sub-30s inference (avoids Cloudflare timeout)
        cap = cv2.VideoCapture(vid_path)
        raw_frames = []
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            raw_frames.append(frame)
        cap.release()

        if not raw_frames:
            raise Exception("No frames extracted from video.")

        total_raw = len(raw_frames)
        # Target ~32 frames: high temporal fidelity for ASL while finishing in ~35-45s (Cloudflare timeout is 100s)
        target_count = min(32, total_raw)
        step = max(1, total_raw // target_count)
        
        sampled_frames = []
        for i in range(0, total_raw, step):
            if len(sampled_frames) >= 32:
                break
            frame = raw_frames[i]
            h, w = frame.shape[:2]
            max_dim = 480
            if max(h, w) > max_dim:
                scale = max_dim / float(max(h, w))
                frame = cv2.resize(frame, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            sampled_frames.append(frame_rgb)

        total_frames = len(sampled_frames)
        print(f"[-] Selected {total_frames} frames (from {total_raw} raw frames). Target processing time: ~35-45s...")

        # Disable empty_cache during loop for 2x memory speedup
        orig_empty_cache = torch.cuda.empty_cache
        torch.cuda.empty_cache = lambda: None

        sequence_joints = []
        cached_bbox = None
        cached_cam_int = None

        try:
            for idx, img_np in enumerate(sampled_frames):
                # Silence internal spam
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    try:
                        # Once we have cached bbox and cam_int, both ViTDet and MoGe-2 are 100% skipped!
                        if cached_bbox is not None and cached_cam_int is not None:
                            output = estimator_0.process_one_image(
                                img_np,
                                bboxes=cached_bbox,
                                cam_int=cached_cam_int,
                                inference_type="full"
                            )
                        else:
                            output = estimator_0.process_one_image(img_np, inference_type="full")
                    except Exception:
                        output = estimator_0.process_one_image(img_np, inference_type="full")

                if not output or len(output) == 0:
                    sequence_joints.append(sequence_joints[-1] if len(sequence_joints) > 0 else [[0.0]*3]*70)
                    continue

                largest_person = None
                max_area = 0
                for person in output:
                    bbox = person.get("bbox", [0, 0, 0, 0])
                    area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
                    if area > max_area:
                        max_area = area
                        largest_person = person

                if largest_person is not None:
                    # Cache bbox with generous headroom and arm span so raised gestures don't clip
                    if cached_bbox is None:
                        bx1, by1, bx2, by2 = largest_person["bbox"]
                        pad_x = (bx2 - bx1) * 0.4
                        pad_top = (by2 - by1) * 0.6
                        pad_bottom = (by2 - by1) * 0.2
                        h, w = img_np.shape[:2]
                        cached_bbox = np.array([[
                            max(0, bx1 - pad_x),
                            max(0, by1 - pad_top),
                            min(w, bx2 + pad_x),
                            min(h, by2 + pad_bottom)
                        ]], dtype=np.float32)

                    # Cache camera intrinsics as a CUDA float32 Tensor (skips MoGe-2!)
                    if cached_cam_int is None and "focal_length" in largest_person:
                        fl = float(largest_person["focal_length"])
                        h, w = img_np.shape[:2]
                        cached_cam_int = torch.tensor(
                            [[[fl, 0.0, w / 2.0], [0.0, fl, h / 2.0], [0.0, 0.0, 1.0]]],
                            dtype=torch.float32,
                            device="cuda"
                        )

                    # Return the 70 keypoints in MHR70 format (matches mhrMapper.js)
                    joints = largest_person["pred_keypoints_3d"] # (70, 3)
                    sequence_joints.append(joints.tolist())
                else:
                    sequence_joints.append(sequence_joints[-1] if len(sequence_joints) > 0 else [[0.0]*3]*70)

                print(f"\r[-] Progress: {int((idx + 1) / total_frames * 100)}% ({idx + 1}/{total_frames})", end="", flush=True)

        finally:
            torch.cuda.empty_cache = orig_empty_cache

        print("\n[+] Inference complete! Sending JSON keypoints...")
        return JSONResponse(content={"frames": sequence_joints})
        
    except Exception as e:
        print(f"ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- CLOUDFLARE TUNNEL SETUP ---
def start_cloudflared():
    cloudflared_path = f"{WORK_DIR}/cloudflared"
    if not os.path.exists(cloudflared_path) or os.path.getsize(cloudflared_path) < 1000000:
        print("[-] Downloading Cloudflare Tunnel binary...")
        urllib.request.urlretrieve(
            "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64",
            cloudflared_path,
        )
        os.chmod(cloudflared_path, 0o755)

    print("[-] Starting Cloudflare Tunnel...")
    process = subprocess.Popen(
        [cloudflared_path, "tunnel", "--url", "http://127.0.0.1:8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
        errors="ignore",
    )
    tunnel_found = False
    for line in iter(process.stdout.readline, ""):
        if not line:
            break
        if not tunnel_found:
            match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
            if match:
                print("\n" + "=" * 60)
                print(f"🌍 PUBLIC API URL: {match.group(0)}")
                print("=" * 60 + "\n")
                tunnel_found = True

threading.Thread(target=start_cloudflared, daemon=True).start()

if __name__ == "__main__":
    nest_asyncio.apply()
    uvicorn.run(app, host="0.0.0.0", port=8000)
""")

add_markdown("# 3. Run the Server")
add_code("""
# Make sure we run it from the correct directory so imports work
import os
os.chdir("/kaggle/working/sam-3d-body")
!python /kaggle/working/sam-3d-body/server.py
""")

notebook = {
    "nbformat": 4,
    "nbformat_minor": 0,
    "metadata": {
        "colab": {
            "name": "SignBridge_MHR_Backend.ipynb",
        },
        "kernelspec": {
            "name": "python3",
            "display_name": "Python 3"
        }
    },
    "cells": cells
}

with open("SignBridge_MHR_Backend.ipynb", "w") as f:
    json.dump(notebook, f, indent=2)
print("MHR Notebook generated.")
