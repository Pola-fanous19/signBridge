import torch
import torchvision

try:
    print("[*] Loading NLF model...")
    # Load on CPU
    model = torch.jit.load("nlf.torchscript", map_location="cpu").eval()
    print("[+] NLF model loaded.")
    
    print("\n--- SCHEMA ---")
    print(model.detect_smpl_batched.schema)
    print("--------------\n")
    
except Exception as e:
    print("[!] Error loading or printing schema:", e)
    
    try:
        print("[!] Available methods:", [m for m in dir(model) if not m.startswith("_")])
    except:
        pass
