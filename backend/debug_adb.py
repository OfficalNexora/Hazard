import sys
import os
import subprocess
import time

# Add current dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from adb_worker import adb_worker

def run_cmd(cmd):
    print(f"Executing: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        print(f"  Return code: {result.returncode}")
        print(f"  STDOUT: {result.stdout.strip()}")
        print(f"  STDERR: {result.stderr.strip()}")
        return result
    except Exception as e:
        print(f"  Error: {e}")
        return None

def test_diagnostics():
    print("--- COMPREHENSIVE DIAGNOSTICS ---")
    
    # 1. SSHPass help to check if it runs at all
    print("\n[1] Testing sshpass binary:")
    run_cmd([adb_worker.sshpass_path, "-V"])
    
    # 2. ADB state
    print("\n[2] Testing ADB device:")
    run_cmd([adb_worker.adb_path, "devices"])
    
    # 3. Detection
    user = adb_worker.detect_termux_user()
    print(f"\n[3] Detected Termux User: {user}")
    
    # 4. Port Check (Android side)
    print("\n[4] Checking port 8022 on Android:")
    run_cmd([adb_worker.adb_path, "shell", "netstat -ln | grep 8022"])
    
    # 5. SSH Test with sshpass to 'echo hello'
    print("\n[5] Testing SSH authentication with sshpass (echo hello):")
    if user:
        ssh_cmd = [
            adb_worker.sshpass_path, "-p", "5090",
            "ssh", "-p", "8022", "-o", "StrictHostKeyChecking=no",
            f"{user}@localhost", "echo 'SSH_AUTH_WORKING'"
        ]
        run_cmd(ssh_cmd)

if __name__ == "__main__":
    test_diagnostics()
