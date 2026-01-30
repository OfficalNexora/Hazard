import os
import subprocess
import sys
import shutil

ROOT_DIR = os.getcwd()
NATIVE_DIR = os.path.join(ROOT_DIR, "native_standalone")
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")
DIST_DIR = os.path.join(ROOT_DIR, "dist_native")

def build():
    if not os.path.exists(DIST_DIR):
        os.makedirs(DIST_DIR)
        
    print("\n--- BUILDING STANDALONE NATIVE EXE ---")
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name", "NEXORA-NATIVE",
        "--add-data", f"{BACKEND_DIR};backend",
        "--add-data", f"{NATIVE_DIR}/core;core",
        "--add-data", f"{NATIVE_DIR}/assets;assets",
        
        # Dependencies
        "--collect-all", "customtkinter",
        "--collect-all", "cv2",
        "--collect-all", "zmq",
        "--collect-all", "PIL",
        
        # Hidden Imports
        "--hidden-import", "zmq.utils.strtypes",
        "--hidden-import", "PIL._tkinter_resample",
        "--hidden-import", "backend.state_manager",
        "--hidden-import", "backend.event_store",
        "--hidden-import", "backend.diorama_model",
        "--hidden-import", "backend.pathfinder",
        "--hidden-import", "core.map_view",
        "--hidden-import", "core.bridge",
        
        f"{NATIVE_DIR}/app.py"
    ]
    
    subprocess.run(cmd, shell=True)
    print("\n[Build] NEXORA-NATIVE.exe is ready in the 'dist' folder.")

if __name__ == "__main__":
    build()
