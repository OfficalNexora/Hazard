# I use this build script to automate the packaging of my station into standalone 
# executables, ensuring it can be deployed on machines without Python installed.

import os
import subprocess
import sys
import shutil

# I've defined these root directories to keep my build context consistent.
ROOT_DIR = os.getcwd()
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")
WORKER_DIR = os.path.join(ROOT_DIR, "worker")
DIST_DIR = os.path.join(ROOT_DIR, "dist_release")

def run_command(cmd, cwd=None):
    # My internal helper to execute build commands and track failures.
    print(f"Executing My Build Command: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, shell=True)
    if result.returncode != 0:
        print(f"I hit a failure executing: {cmd}")

def ensure_dir(path):
    # I use this to clean up my previous build artifacts before starting a fresh run.
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)

def build_frontend():
    # I'm compiling my Next.js frontend into a static export 
    # so my backend can serve it without needing a Node.js runtime.
    print("\n--- I'm Building My Frontend (Next.js) ---")
    run_command(["npm", "install"], cwd=FRONTEND_DIR)
    run_command(["npm", "run", "build"], cwd=FRONTEND_DIR)
    
    # I'm copying my final 'out' folder into my backend static directory.
    static_dest = os.path.join(BACKEND_DIR, "static")
    if os.path.exists(static_dest):
        shutil.rmtree(static_dest)
    
    out_dir = os.path.join(FRONTEND_DIR, "out")
    if os.path.exists(out_dir):
        shutil.copytree(out_dir, static_dest)
    else:
        print("I couldn't find my frontend 'out' directory. Static serving will fail.")

def build_server_exe():
    # I'm using PyInstaller to package my entire Command Center hub into a single EXE.
    # I've bundled the backend and frontend assets inside the executable.
    print("\n--- I'm Packaging My Nexora Launcher EXE ---")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed", # I want this to run as a clean GUI app.
        "--name", "MOD-EVAC-SERVER",
        "--add-data", f"{BACKEND_DIR};backend",
        "--add-data", f"{FRONTEND_DIR}/out;frontend/out",
        "--add-data", f"{ROOT_DIR}/frontend_public/out;frontend_public/out",
        "--hidden-import", "engineio.async_drivers.threading",
        "--hidden-import", "uvicorn.loops.auto",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.lifespan.on",
        "--hidden-import", "win32timezone",
        "nexus_launcher.py"
    ]
    run_command(cmd)

def build_worker_exe():
    # I'm packaging my AI worker separately so I can distribute 
    # computation across multiple nodes in the field.
    print("\n--- I'm Packaging My Worker EXE ---")
    model_path = os.path.join(WORKER_DIR, "yolov8n.pt")
      
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed", 
        "--name", "MOD-EVAC-WORKER",
        "--collect-all", "ultralytics",
        "--collect-all", "cv2"
    ]
    
    if os.path.exists(model_path):
        # I'm embedding my YOLO weights directly into the worker binary.
        cmd.extend(["--add-data", f"{model_path};."])
        
    cmd.append(f"{WORKER_DIR}/worker_app.py")
    
    run_command(cmd)

def main():
    if not os.path.exists(DIST_DIR):
        os.makedirs(DIST_DIR)
    
    # I've commented these out to prevent unnecessary rebuilds while I'm testing the worker.
    build_frontend()
    build_server_exe()
    
    # 3. I'm focusing on the worker build for now.
    build_worker_exe()
    
    print("\nI've completed my build process. Checking my 'dist' folder for the final EXEs.")

if __name__ == "__main__":
    main()
