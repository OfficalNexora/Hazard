import os
import subprocess
import threading
import time
from typing import Optional, List

class ADBWorker:
    """
    Integrates ADB tools for SMS and Calling via Termux.
    Uses temporary batch files to ensure compatibility with Windows-specific TTY/quoting.
    """
    def __init__(self, adb_dir: Optional[str] = None):
        if adb_dir is None:
            self.base_dir = os.path.dirname(os.path.abspath(__file__))
            self.adb_dir = os.path.join(self.base_dir, "platform-tools-latest-windows", "platform-tools")
        else:
            self.adb_dir = adb_dir
            
        self.adb_path = os.path.join(self.adb_dir, "adb.exe")
        self.sshpass_path = os.path.join(self.adb_dir, "sshpass.exe")
        self.default_pass = "5090"

        # Ensure system SSH is in path
        ssh_dir = r"C:\Windows\System32\OpenSSH"
        if os.path.exists(ssh_dir) and ssh_dir not in os.environ["PATH"]:
            os.environ["PATH"] += os.pathsep + ssh_dir

    def _run_via_bat(self, cmd_line: str, timeout: int = 25) -> bool:
        """Writes a temporary batch file and executes it to match manual terminal behavior"""
        bat_name = f"temp_worker_{int(time.time() * 1000)}.bat"
        bat_path = os.path.join(self.adb_dir, bat_name)
        
        try:
            with open(bat_path, "w") as f:
                f.write("@echo off\n")
                f.write(f"cd /d \"{self.adb_dir}\"\n")
                f.write(f"{cmd_line}\n")
            
            # Using shell=True for the batch runner
            result = subprocess.run([bat_path], capture_output=True, text=True, timeout=timeout, shell=True)
            if result.returncode == 0:
                return True
            else:
                print(f"[ADBWorker] BAT FAILED ({result.returncode})")
                print(f"STDOUT: {result.stdout}")
                print(f"STDERR: {result.stderr}")
                return False
        except Exception as e:
            print(f"[ADBWorker] BAT EXCEPTION: {e}")
            return False
        finally:
            if os.path.exists(bat_path):
                try: os.remove(bat_path)
                except: pass

    def is_device_connected(self) -> bool:
        try:
            result = subprocess.run([self.adb_path, "get-state"], capture_output=True, text=True, timeout=5)
            return "device" in result.stdout.lower()
        except: return False

    def detect_termux_user(self) -> Optional[str]:
        """Robustly detects the Termux user ID (e.g. u0_a10443)"""
        try:
            # Output format: package:com.termux uid:10443
            result = subprocess.run([self.adb_path, "shell", "pm", "list", "packages", "-U", "com.termux"], 
                                   capture_output=True, text=True, timeout=5)
            # Find the line that is EXACTLY for com.termux (not .api or .boot)
            for line in result.stdout.splitlines():
                if "package:com.termux uid:" in line or "package:com.termux " in line:
                    if "uid:" in line:
                        uid_str = line.split("uid:")[-1].strip()
                        app_id = int(uid_str) % 100000
                        return f"u0_a{app_id}"
        except: pass
        # Fallback to the one that worked for the user manual test
        return "u0_a10443"

    def setup_tunnel(self):
        """Matches: adb.exe forward tcp:8022 tcp:8022"""
        subprocess.run([self.adb_path, "forward", "tcp:8022", "tcp:8022"], capture_output=True, timeout=5)

    def ensure_sshd_running(self):
        """Optional helper to ensure Termux is awake and sshd is running"""
        # Triggers the 'sshd' execution via Termux:Tasker or standard extra intent
        subprocess.run([self.adb_path, "shell", "am", "start", "-n", "com.termux/com.termux.app.TermuxActivity", 
                        "--es", "com.termux.execute", "sshd"], capture_output=True, timeout=5)
        time.sleep(2)

    def send_sms(self, phone: str, message: str, password: Optional[str] = None) -> bool:
        """Calls the dedicated trigger_sms.bat using Environment Variables for stability"""
        pw = password or self.default_pass
        user = self.detect_termux_user()
        bat_path = os.path.join(self.adb_dir, "trigger_sms.bat")
        
        print(f"[ADBWorker] Triggering SMS via Environment (User: {user}) for {phone}...")
        
        # Set environment variables for the batch script
        env = os.environ.copy()
        env["SMS_PHONE"] = phone
        env["SMS_MSG"] = message
        env["SMS_PASS"] = pw
        env["SMS_USER"] = user

        try:
            # Log start
            with open("adb_debug.log", "a") as f:
                f.write(f"\n[SMS START] To: {phone} | Time: {time.time()}\n")
                f.write(f"Env: {env}\n")

            # We run the batch file without capturing output so sshpass can see the TTY
            # however, if there IS no TTY (background service), this might still fail.
            # We explicitly connect stdin to likely avoid simple pipe errors, but sshpass is strict.
            result = subprocess.run([bat_path], env=env,
                                   cwd=self.adb_dir, text=True, timeout=30)
            
            with open("adb_debug.log", "a") as f:
                f.write(f"[SMS END] Return Code: {result.returncode}\n")
            
            if result.returncode == 0:
                print("[ADBWorker] SMS SUCCESS")
                return True
            else:
                print(f"[ADBWorker] SMS FAILED ({result.returncode})")
                return False

        except Exception as e:
            with open("adb_debug.log", "a") as f:
                f.write(f"[SMS EXCEPTION] {e}\n")
            print(f"[ADBWorker] EXCEPTION: {e}")
            return False

    def make_call(self, phone: str, password: Optional[str] = None) -> bool:
        user = self.detect_termux_user()
        if not user: return False
        
        self.ensure_sshd_running()
        self.setup_tunnel()
        pw = password or self.default_pass
        
        # Using 127.0.0.1 for stability
        cmd = f'sshpass.exe -p {pw} ssh -p 8022 -o StrictHostKeyChecking=no {user}@127.0.0.1 "termux-telephony-call {phone}"'
        
        print(f"[ADBWorker] Triggering Call via BAT: {phone}")
        return self._run_via_bat(cmd)

    def play_local_audio(self, mp3_path: str):
        ps_cmd = f'powershell -ExecutionPolicy Bypass -Command "Add-Type -AssemblyName PresentationCore; $p = New-Object System.Windows.Media.MediaPlayer; $p.Open(\'{mp3_path}\'); $p.Play(); Start-Sleep 5"'
        threading.Thread(target=lambda: subprocess.run(ps_cmd, shell=True), daemon=True).start()

adb_worker = ADBWorker()
