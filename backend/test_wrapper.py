import subprocess
import os
import time

sshpass = r"C:\Users\Victo\Hazard\backend\platform-tools-latest-windows\platform-tools\sshpass.exe"
wrapper = r"C:\Users\Victo\Hazard\backend\ssh_wrapper.bat"

def test_wrapper():
    cmd = f'"{sshpass}" -p 5090 ssh -p 8022 -o StrictHostKeyChecking=no u0_a10443@localhost ls'
    print(f"Running via wrapper: {cmd}")
    
    # Run wrapper
    subprocess.run([wrapper, cmd], shell=True)
    
    # Read results
    if os.path.exists("out.txt"):
        with open("out.txt", "r") as f:
            print(f"OUT: {f.read()}")
    if os.path.exists("status.txt"):
        with open("status.txt", "r") as f:
            print(f"STATUS: {f.read()}")

if __name__ == "__main__":
    test_wrapper()
