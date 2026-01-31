import subprocess
import time
import os
import sys

# Add current dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from adb_worker import adb_worker

def debug_interactive():
    user = adb_worker.detect_termux_user()
    if not user:
        print("User not detected.")
        return

    # Force tunnel setup
    adb_worker.setup_tunnel()
    time.sleep(1)

    # Command to run: ssh -p 8022 -o StrictHostKeyChecking=no user@localhost
    # Using -tt to force a pseudo-terminal
    cmd = ["ssh", "-tt", "-p", "8022", "-o", "StrictHostKeyChecking=no", f"{user}@localhost", "whoami"]
    
    print(f"Executing: {' '.join(cmd)}")
    
    # We use subprocess.Popen to interact
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=0
    )

    # Read output to find password prompt
    output = ""
    start_time = time.time()
    while time.time() - start_time < 10:
        char = process.stdout.read(1)
        if not char:
            break
        output += char
        print(char, end="", flush=True)
        if "password:" in output.lower():
            print("\n[DEBUG] Found password prompt!")
            # Send password
            process.stdin.write("5090\n")
            process.stdin.flush()
            # Clear output buffer to see next response
            output = ""
        if "u0_a" in output or "termux" in output:
             print("\n[DEBUG] Success detected in output!")
             break
    
    process.terminate()
    print("\n--- DEBUG FINISHED ---")

if __name__ == "__main__":
    debug_interactive()
