import os
import sys
import subprocess
import yaml
import time

# --- SELF-INSTALLER ---
# I've added this block to ensure all my specialized libraries are installed 
# before I start the heavy lifting. This makes my environment portable.
def install_dependencies():
    required = ["ultralytics", "pyyaml", "torch", "torchvision", "torchaudio"]
    print("I'm checking my system dependencies...")
    for lib in required:
        try:
            __import__(lib if lib != "pyyaml" else "yaml")
        except ImportError:
            print(f"I found {lib} is missing. I'm installing it now...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", lib])
    print("I'm all set with the dependencies.")

# I run this immediately on startup.
install_dependencies()

# Now I can safely import Ultralytics.
from ultralytics import YOLO
import torch

# I've defined the absolute paths for my datasets here.
DATASET_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../datasets"))
HAZARD_DATA_YAML = os.path.join(DATASET_DIR, "hazard_detection/data.yaml")

def train_model():
    # I'm checking if I have a CUDA-capable GPU. 
    # With a 16GB GPU, I can really push the resolution and batch size.
    device = 0 if torch.cuda.is_available() else "cpu"
    print(f"I am using device: {'GPU (16GB mode)' if device == 0 else 'CPU (WARNING: This will be slow!)'}")

    # I'm starting with the Nano OBB model but since I have a 16GB GPU, 
    # I'm going to use 'yolov8s-obb' for significantly better accuracy.
    model_name = "yolov8s-obb.pt" 
    print(f"I'm initializing my model base: {model_name}")
    model = YOLO(model_name) 

    # I have to warn that indexing 190k+ files takes time.
    print("\n---------------------------------------------------------")
    print("I'm starting the indexing of 190,000+ files.")
    print("WARNING: This might look like it's 'stuck' for 15-30 minutes.")
    print("I am building the label cache for my tiles. Please wait...")
    print("---------------------------------------------------------\n")

    results = model.train(
        data=HAZARD_DATA_YAML,
        task="obb",        
        epochs=150,        
        imgsz=1024,        # I've bumped this to 1024 because I have 16GB VRAM. This will find tiny debris.
        batch=32,          # Optimized for 16GB VRAM. I can fit a larger batch now.
        patience=50,       
        
        # Advanced Processing 
        optimizer='AdamW', 
        lr0=0.001,         
        lrf=0.01,          
        dropout=0.1,       
        label_smoothing=0.1, 
        
        # My custom augmentations for fire/smoke/debris.
        mosaic=1.0,        
        mixup=0.2,         
        copy_paste=0.2,    
        scale=0.6,         
        
        project="MOD-EVAC-MS",
        name="hazard_obb_pro_16gb",
        exist_ok=True,
        workers=8,         # I'm using 8 workers to feed my GPU faster.
        device=device,
        multi_scale=True   
    )
    
    print("Training Complete. I've stored the final specialized weights in runs/obb/hazard_obb_pro_16gb")
    return results

if __name__ == "__main__":
    if not os.path.exists(HAZARD_DATA_YAML):
        print(f"Error: I can't find my dataset config at {HAZARD_DATA_YAML}")
    else:
        with open(HAZARD_DATA_YAML, 'r') as f:
            y = yaml.safe_load(f)
            print(f"I am training on: {y.get('names', 'Unknown')}")

        # BOOTING TRAINING
        train_model()
