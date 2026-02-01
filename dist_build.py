# I use this build script to automate the packaging of the station into standalone 
# executables, ensuring it can be deployed on machines without Python installed.

import os
import subprocess
import sys
import shutil

# defined these root directories to the build context consistent.
ROOT_DIR = os.getcwd()
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")
WORKER_DIR = os.path.join(ROOT_DIR, "worker")
DIST_DIR = os.path.join(ROOT_DIR, "dist_release")

def run_command(cmd, cwd=None):
    # helper to execute build commands and track failures.
    print(f"Executing Build Command: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, shell=True)
    if result.returncode != 0:
        print(f"I hit a failure executing: {cmd}")

def ensure_dir(path):
    # I use this to clean up my previous build artifacts before starting a fresh run.
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)

def build_frontend():
    # compiling the Next.js frontend into a static export 
    # so backend can serve it without needing a Node.js runtime.
    print("\n--- I'm Building My Frontend (Next.js) ---")
    run_command(["npm", "install"], cwd=FRONTEND_DIR)
    run_command(["npm", "run", "build"], cwd=FRONTEND_DIR)
    
    # copying the final 'out' folder into my backend static directory.
    static_dest = os.path.join(BACKEND_DIR, "static")
    if os.path.exists(static_dest):
        shutil.rmtree(static_dest)
    
    out_dir = os.path.join(FRONTEND_DIR, "out")
    if os.path.exists(out_dir):
        shutil.copytree(out_dir, static_dest)
    else:
        print("I couldn't find my frontend 'out' directory. Static serving will fail.")

def build_server_exe():
    # using PyInstaller to package my entire Command Center hub into a single EXE.
    # bundled the backend and frontend assets inside the executable.
    print("\n--- [Build]Packaging My Nexora Launcher EXE ---")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed", # I want this to run as a clean GUI app.
        "--name", "MOD-EVAC-SERVER",
        "--add-data", f"{BACKEND_DIR};backend",
        "--add-data", f"{FRONTEND_DIR}/out;frontend/out",
        "--add-data", f"{ROOT_DIR}/frontend_public/out;frontend_public/out",
        "--add-data", f"{ROOT_DIR}/standalone_app.py;.",
        
        # === CRITICAL: Collect all dependencies ===
        "--collect-all", "fastapi",
        "--collect-all", "uvicorn",
        "--collect-all", "starlette",
        "--collect-all", "pydantic",
        "--collect-all", "anyio",
        "--collect-all", "webview",
        "--collect-all", "clr_loader",
        "--collect-all", "pythonnet",
        
        # === FastAPI/Uvicorn core imports ===
        "--hidden-import", "fastapi",
        "--hidden-import", "fastapi.middleware",
        "--hidden-import", "fastapi.middleware.cors",
        "--hidden-import", "fastapi.staticfiles",
        "--hidden-import", "fastapi.responses",
        "--hidden-import", "uvicorn",
        "--hidden-import", "uvicorn.main",
        "--hidden-import", "uvicorn.config",
        "--hidden-import", "uvicorn.loops.auto",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.protocols.http.h11_impl",
        "--hidden-import", "uvicorn.protocols.websockets.auto",
        "--hidden-import", "uvicorn.protocols.websockets.websockets_impl",
        "--hidden-import", "uvicorn.lifespan.on",
        "--hidden-import", "uvicorn.lifespan.off",
        "--hidden-import", "uvicorn.logging",
        
        # === Starlette (FastAPI dependency) ===
        "--hidden-import", "starlette",
        "--hidden-import", "starlette.middleware",
        "--hidden-import", "starlette.middleware.cors",
        "--hidden-import", "starlette.routing",
        "--hidden-import", "starlette.responses",
        "--hidden-import", "starlette.staticfiles",
        "--hidden-import", "starlette.websockets",
        
        # === AsyncIO/Networking ===
        "--hidden-import", "anyio",
        "--hidden-import", "anyio._backends._asyncio",
        "--hidden-import", "h11",
        "--hidden-import", "httptools",
        "--hidden-import", "websockets",
        "--hidden-import", "engineio.async_drivers.threading",
        
        # === Pydantic (data validation) ===
        "--hidden-import", "pydantic",
        "--hidden-import", "pydantic.fields",
        "--hidden-import", "pydantic_core",
        
        # === Database/Serial ===
        "--hidden-import", "sqlite3",
        "--hidden-import", "serial",
        "--hidden-import", "serial.tools.list_ports",
        
        # === Windows-specific ===
        "--hidden-import", "win32timezone",
        
        # === 3D Digital Twin modules ===
        "--hidden-import", "backend.diorama_model",
        "--hidden-import", "backend.camera_mapper",
        "--hidden-import", "backend.pathfinder",
        "--hidden-import", "backend.event_store",
        "--hidden-import", "backend.state_manager",
        "--hidden-import", "backend.sensor_worker",
        "--hidden-import", "backend.vision_worker",
        "--hidden-import", "backend.control_worker",
        "--hidden-import", "backend.worker_manager",
        "--hidden-import", "backend.database",
        
        # === NumPy for 3D math ===
        "--hidden-import", "numpy",
        "--hidden-import", "webview",
        "--hidden-import", "clr_loader",
        "--hidden-import", "pythonnet",
        
        "nexus_launcher.py"
    ]
    run_command(cmd)



def build_worker_exe():
    # packaging the AI workers separately so I can distribute 
    # computation across multiple nodes in the field.
    print("\n--- [Build]Packaging My Worker EXE ---")
    model_path = os.path.join(WORKER_DIR, "yolov8n.pt")

    # HEY IF YOU COMMITED IN GIT MAKE SURE TO ADD THE IMPORT YOU ADDED - ernes 
    # I added the import for the ultralytics and cv2 packages.      
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
        # embedding the AI weights directly into the worker binary.
        cmd.extend(["--add-data", f"{model_path};."])
        
    cmd.append(f"{WORKER_DIR}/worker_app.py")
    
    run_command(cmd)

def main():
    if not os.path.exists(DIST_DIR):
        os.makedirs(DIST_DIR)
    
    build_frontend()
    build_server_exe()
    
    # -Focusing on the worker build for now.
    build_worker_exe()
    
    print("\n[Build] Completed my build process. Checking my 'dist' folder for the final EXEs.")

if __name__ == "__main__":
    main()
