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
        """
        Edits the trigger_sms.bat file directly to set PHONE and MSG, then executes it.
        This ensures we use the exact batch logic provided by the user.
        """
        bat_path = os.path.join(self.adb_dir, "trigger_sms.bat")
        password = password or self.default_pass
        
        # Clean message for batch file (basic escaping)
        safe_message = message.replace('"', '\\"')
        
        # Detect correct user
        correct_user = self.detect_termux_user() or "u0_a10443"
        
        try:
            # 1. Read existing content
            with open(bat_path, "r") as f:
                lines = f.readlines()
            
            # 2. Update configuration lines
            new_lines = []
            # Ensure SSH is in PATH for the batch execution
            new_lines.append("SET PATH=%PATH%;C:\\Windows\\System32\\OpenSSH\n")
            
            for line in lines:
                strip_line = line.strip()
                if strip_line.startswith("SET PHONE="):
                    new_lines.append(f"SET PHONE={phone}\n")
                elif strip_line.startswith("SET MSG="):
                    new_lines.append(f"SET MSG=\"{safe_message}\"\n")
                elif strip_line.startswith("SET PASS="):
                     new_lines.append(f"SET PASS={password}\n")
                elif "adb.exe shell whoami" in line:
                    # Override the auto-detection line with the correct user
                    new_lines.append(f":: Auto-detection replaced by worker\n")
                    new_lines.append(f"SET USER={correct_user}\n")
                elif "sshpass.exe" in line:
                    # Ensure 127.0.0.1 and verbose
                    safe_line = line.replace("localhost", "127.0.0.1")
                    safe_line = safe_line.replace("sshpass.exe -p", "sshpass.exe -v -p")
                    new_lines.append(safe_line)
                else:
                    new_lines.append(line)
            
            
            # 3. Write back changes
            with open(bat_path, "w") as f:
                f.writelines(new_lines)
                
            print(f"[ADBWorker] Updated {bat_path} with Phone={phone}")
            
            # 4. Execute the batch file
            # Use CREATE_NEW_CONSOLE to ensure sshpass has a valid console to interact with
            # This mimics the user running the batch file manually
            print("[ADBWorker] Executing batch file in new console...")
            p = subprocess.Popen([bat_path], cwd=self.adb_dir, creationflags=subprocess.CREATE_NEW_CONSOLE)
            p.wait()
            
            if p.returncode == 0:
                print("[ADBWorker] SMS Batch Executed Successfully")
                return True
            else:
                print(f"[ADBWorker] SMS Batch Failed (Code {p.returncode})")
                return False

        except Exception as e:
            print(f"[ADBWorker] Exception sending SMS: {e}")
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
