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
        Generates a unique batch file for each SMS and executes it in a new console.
        Uses ADB + Termux SSH to send real SMS from an Android phone.
        """
        import uuid
        
        # Unique file in the ADB directory
        temp_filename = f"sms_{uuid.uuid4().hex[:8]}.bat"
        temp_bat_path = os.path.join(self.adb_dir, temp_filename)
        
        password = password or self.default_pass
        
        # Escape quotes in message for batch file
        safe_message = message.replace('"', "'")
        
        # Generate the batch file content using user's template
        bat_content = f'''@echo off
:: --- AUTO-GENERATED SMS SCRIPT ---
SET PHONE={phone}
SET MSG="{safe_message}"
SET PASS={password}

echo [1/3] Starting USB Tunnel...
%~dp0adb.exe forward tcp:8022 tcp:8022

echo [2/3] Detecting Phone User...
for /f "tokens=*" %%i in ('%~dp0adb.exe shell whoami') do set USER=%%i

echo [3/3] Sending SMS via %USER%...
%~dp0sshpass.exe -p %PASS% ssh -p 8022 -o StrictHostKeyChecking=no %USER%@localhost "termux-sms-send -n %PHONE% %MSG%"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo SUCCESS: Message sent to {phone}
) else (
    echo.
    echo FAILED: Check if sshd is running in Termux
)

timeout /t 3 >nul
'''
        
        try:
            # Write the batch file
            with open(temp_bat_path, "w") as f:
                f.write(bat_content)
                
            print(f"[ADBWorker] Created batch: {temp_filename} for {phone}")
            
            # Execute in new console window (visible to user)
            print(f"[ADBWorker] Executing SMS to {phone}...")
            p = subprocess.Popen(
                [temp_bat_path], 
                cwd=self.adb_dir, 
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
            p.wait()
            
            if p.returncode == 0:
                print(f"[ADBWorker] SMS to {phone} completed successfully")
                return True
            else:
                print(f"[ADBWorker] SMS to {phone} failed (code {p.returncode})")
                return False

        except Exception as e:
            print(f"[ADBWorker] Exception sending SMS: {e}")
            return False
        finally:
            # Cleanup temp file
            if os.path.exists(temp_bat_path):
                try:
                    os.remove(temp_bat_path)
                except:
                    pass

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
