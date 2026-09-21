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

add_markdown("# 1. Environment Setup\nInstall dependencies, download NLF, and setup Headless Blender.")
add_code("""
import os
%cd /content

print("[-] Installing dependencies for NLF server + OpenCV...")
!pip install -q fastapi uvicorn pydantic nest-asyncio smplfitter opencv-python-headless pyngrok python-multipart

# Download the NLF checkpoint
if not os.path.exists("/content/nlf_l_multi_0.3.2.torchscript"):
    !wget -q https://github.com/isarandi/nlf/releases/download/v0.3.2/nlf_l_multi_0.3.2.torchscript

# Download Headless Blender
if not os.path.exists("/content/blender-4.5.0-linux-x64"):
    !wget -q https://download.blender.org/release/Blender4.5/blender-4.5.0-linux-x64.tar.xz
    !tar -xf blender-4.5.0-linux-x64.tar.xz

# Clone and ZIP the public SMPL-X Blender Add-on
if not os.path.exists("/content/smplx_blender_addon"):
    !git clone https://gitlab.tuebingen.mpg.de/jtesch/smplx_blender_addon.git
    !cd /content/smplx_blender_addon && zip -r -q ../smplx_addon.zip .

print("[+] NLF + Blender environment ready!")
""")

add_markdown("# 2. The Conversion Script Generator\nCreates the Python script that Blender will execute internally.")
add_code("""
conversion_script = \"\"\"
import bpy
import sys

# Clear default cube and scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Install the Add-on natively for Blender 4.2+
bpy.ops.extensions.package_install(filepath='/content/smplx_addon.zip')
try:
    bpy.ops.preferences.addon_enable(module='smplx_addon')
except Exception:
    pass # Extensions might be auto-enabled in 4.5

# Import the .npz file (which we will create dynamically from NLF's output)
try:
    # NLF outputs SMPL, not SMPL-X, but the addon usually handles SMPL .npz imports just fine 
    # if the keys match what the script expects.
    bpy.ops.import_scene.smplx(filepath='/content/results.npz')
except Exception as e:
    print(f"Error importing NPZ: {e}")

# Export the baked animation to GLB for React
bpy.ops.export_scene.gltf(
    filepath='/content/new_word.glb',
    export_format='GLB',
    export_animations=True,
    export_bake_kinematics=True
)
\"\"\"

with open("/content/auto_convert.py", "w") as f:
    f.write(conversion_script)
""")

add_markdown("# 3. The FastAPI Server (NLF Video Processing)\nProcesses `.webm` videos, runs NLF batched inference, generates `.npz`, and bakes `.glb`.")
add_code("""
%%writefile /content/server.py
import os
import io
import re
import threading
import subprocess
import urllib.request
import cv2
import json

import torch
import torchvision
import numpy as np
from PIL import Image
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import nest_asyncio

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"[-] Using device: {device}")

print("[*] Loading NLF model...")
model = torch.jit.load("/content/nlf_l_multi_0.3.2.torchscript").to(device).eval()
print("[+] NLF model loaded.")

app = FastAPI(title="SignAvatar NLF Backend")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.post("/api/process-video")
async def process_video(video: UploadFile = File(...)):
    try:
        print(f"[-] Received video: {video.filename}")
        
        # 1. Save uploaded video
        vid_path = f"/content/{video.filename}"
        with open(vid_path, "wb") as f:
            f.write(await video.read())
            
        # 2. Extract frames with OpenCV
        cap = cv2.VideoCapture(vid_path)
        frames = []
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frames.append(frame_rgb)
        cap.release()
        
        if not frames:
            raise Exception("No frames extracted from video.")
            
        print(f"[-] Extracted {len(frames)} frames. Running NLF inference...")
        
        # 3. NLF Batched Inference
        # Depending on RAM, we might need to batch this. Let's do it in one pass for short signs.
        frame_tensors = []
        for img_np in frames:
            img_t = torch.from_numpy(img_np).permute(2, 0, 1).to(device) # CHW, uint8
            frame_tensors.append(img_t)
            
        batched_tensor = torch.stack(frame_tensors)
        
        with torch.no_grad():
            pred = model.detect_smpl_batched(batched_tensor)
            
        # 4. Construct NPZ for Blender
        # Extract the necessary keys for SMPL importer
        global_orient = pred.get("global_orient", None)
        body_pose = pred.get("body_pose", None)
        transl = pred.get("transl", None)
        betas = pred.get("betas", None)
        
        npz_dict = {}
        if global_orient is not None:
            npz_dict['global_orient'] = global_orient.cpu().numpy()
        if body_pose is not None:
            npz_dict['body_pose'] = body_pose.cpu().numpy()
        if transl is not None:
            npz_dict['transl'] = transl.cpu().numpy()
        if betas is not None:
            npz_dict['betas'] = betas.cpu().numpy()
            
        print("[-] Saving NPZ file for Blender...")
        np.savez('/content/results.npz', **npz_dict)
        
        # 5. Run Headless Blender
        print("[-] Baking NLF parameters to GLB via Headless Blender...")
        if os.path.exists('/content/new_word.glb'):
            os.remove('/content/new_word.glb')
            
        subprocess.run(["/content/blender-4.5.0-linux-x64/blender", "-b", "-P", "/content/auto_convert.py"], check=True)
        
        if not os.path.exists("/content/new_word.glb"):
            raise Exception("Blender failed to produce GLB file.")
            
        return FileResponse("/content/new_word.glb", media_type="model/gltf-binary", filename=f"{video.filename}.glb")
        
    except Exception as e:
        print(f"ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- CLOUDFLARE TUNNEL SETUP ---
def start_cloudflared():
    cloudflared_path = "/content/cloudflared"
    if not os.path.exists(cloudflared_path):
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
    for line in process.stdout:
        match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
        if match:
            print("\\n" + "=" * 60)
            print(f"🌍 PUBLIC API URL: {match.group(0)}")
            print("=" * 60 + "\\n")
            break

threading.Thread(target=start_cloudflared, daemon=True).start()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
""")

add_markdown("# 4. Run the Server")
add_code("""
!python /content/server.py
""")

notebook = {
    "nbformat": 4,
    "nbformat_minor": 0,
    "metadata": {
        "colab": {
            "name": "SignBridge_NLF_Backend.ipynb",
        },
        "kernelspec": {
            "name": "python3",
            "display_name": "Python 3"
        }
    },
    "cells": cells
}

with open("SignBridge_NLF_Backend.ipynb", "w") as f:
    json.dump(notebook, f, indent=2)
print("NLF Notebook generated.")
