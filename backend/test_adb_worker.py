import sys
import os

# Add current dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from adb_worker import adb_worker

if __name__ == "__main__":
    number = "09614806675"
    print(f"--- FINAL VERIFICATION SMS: {number} ---")
    
    success = adb_worker.send_sms(number, "Baseline Verification Message")
    
    if success:
        print("\n[SUCCESS] SMS integration is working!")
    else:
        print("\n[FAILED] SMS integration failed in automated test.")
        print("Note: If manual command works but this fails, it might be due to tool-specific TTY restrictions.")
