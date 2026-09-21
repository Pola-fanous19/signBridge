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

add_markdown("# 1. Environment Setup\nClone SMPLer-X, install dependencies, and setup Headless Blender.")
add_code("""
import os
%cd /content

# Clone SMPLer-X
if not os.path.exists("/content/SMPLer-X"):
    !git clone https://github.com/caizhongang/SMPLer-X.git

# Install base dependencies (MMPose, MMCV, etc.)
!pip install -q torch torchvision torchaudio
!pip install -q openmim
!mim install -q mmcv-full mmpose mmdet

# Clone the public SMPL-X Blender Add-on
if not os.path.exists("/content/smplx_blender_addon"):
    !git clone https://gitlab.tuebingen.mpg.de/jtesch/smplx_blender_addon.git

# Download Headless Blender
if not os.path.exists("/content/blender-3.6.5-linux-x64"):
    !wget -q https://download.blender.org/release/Blender3.6/blender-3.6.5-linux-x64.tar.xz
    !tar -xf blender-3.6.5-linux-x64.tar.xz

# Install FastAPI and Cloudflare
!pip install -q fastapi uvicorn pydantic nest-asyncio pyngrok python-multipart
""")

add_markdown("# 2. The Conversion Script Generator\nCreates the Python script that Blender will execute internally.")
add_code("""
conversion_script = \"\"\"
import bpy
import sys

# Clear default cube and scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Programmatically load the SMPL-X add-on from the cloned repo
# Note: The addon is usually a zip file or a folder. If it's a folder, we link it to Blender's scripts path.
import shutil
import os

addon_src = '/content/smplx_blender_addon'
addon_dst = '/root/.config/blender/3.6/scripts/addons/smplx_blender_addon'
os.makedirs(os.path.dirname(addon_dst), exist_ok=True)
if not os.path.exists(addon_dst):
    shutil.copytree(addon_src, addon_dst)

bpy.ops.preferences.addon_enable(module='smplx_blender_addon')

# Import the SMPLer-X .npz file using the add-on's specific import command
# (The file path is hardcoded here for the automator)
try:
    bpy.ops.import_scene.smplx(filepath='/content/results.npz')
except Exception as e:
    print(f"Error importing NPZ: {e}")

# Export the baked animation to GLB for React
bpy.ops.export_scene.gltf(
    filepath='/content/new_word.glb',
    export_format='GLB',
    export_animations=True,
    export_bake_kinematics=True # Bakes the complex math down to simple frames
)
\"\"\"

with open("/content/auto_convert.py", "w") as f:
    f.write(conversion_script)
""")

add_markdown("# 3. The FastAPI Server\nRuns the cloud server and handles video processing.")
add_code("""
import os
import sys
import subprocess
import threading
import urllib.request
import re
import tempfile
import nest_asyncio
import uvicorn
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

nest_asyncio.apply()
app = FastAPI(title="SignBridge SMPLer-X Backend")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.post("/api/process-video")
async def process_video(video: UploadFile = File(...)):
    print(f"[-] Received video: {video.filename}")
    
    # 1. Save uploaded video
    vid_path = f"/content/{video.filename}"
    with open(vid_path, "wb") as f:
        f.write(await video.read())
        
    # 2. Run SMPLer-X (Placeholder inference command)
    print("[-] Running SMPLer-X inference...")
    # NOTE: You will need to replace this with the exact SMPLer-X inference command for your specific weights.
    # It should output to /content/results.npz
    # subprocess.run(["python", "/content/SMPLer-X/inference.py", "--video", vid_path, "--output", "/content/results.npz"], check=True)
    
    # Dummy creation of results.npz for the automator if inference fails
    if not os.path.exists("/content/results.npz"):
        open("/content/results.npz", "a").close()

    # 3. Run Headless Blender
    print("[-] Baking SMPL-X parameters to GLB via Headless Blender...")
    subprocess.run(["/content/blender-3.6.5-linux-x64/blender", "-b", "-P", "/content/auto_convert.py"], check=True)
    
    return FileResponse("/content/new_word.glb", media_type="model/gltf-binary", filename=f"{video.filename}.glb")

# --- CLOUDFLARE TUNNEL SETUP ---
def start_cloudflared():
    cloudflared_path = "/content/cloudflared"
    if not os.path.exists(cloudflared_path):
        print("[-] Downloading Cloudflare Tunnel binary...")
        urllib.request.urlretrieve("https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64", cloudflared_path)
        os.chmod(cloudflared_path, 0o755)
    
    print("[-] Starting Cloudflare Tunnel...")
    process = subprocess.Popen(
        [cloudflared_path, "tunnel", "--url", "http://127.0.0.1:8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding='utf-8',
        errors='ignore'
    )
    
    for line in process.stdout:
        match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
        if match:
            print("\\n" + "="*60)
            print(f"🌍 PUBLIC API URL: {match.group(0)}")
            print("="*60 + "\\n")
            break

threading.Thread(target=start_cloudflared, daemon=True).start()

print("\\n🚀 API SERVER STARTING 🚀\\n")
uvicorn.run(app, host="0.0.0.0", port=8000)
""")

notebook = {
    "nbformat": 4,
    "nbformat_minor": 0,
    "metadata": {
        "colab": {
            "name": "SignBridge_SMPLerX_Backend.ipynb",
        },
        "kernelspec": {
            "name": "python3",
            "display_name": "Python 3"
        }
    },
    "cells": cells
}

with open("SignBridge_SMPLerX_Backend.ipynb", "w") as f:
    json.dump(notebook, f, indent=2)
print("Notebook generated.")
