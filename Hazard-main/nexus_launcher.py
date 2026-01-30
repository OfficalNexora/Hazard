import os
import sys
import socket
import threading
import subprocess
import time
import json
import webbrowser
import logging
import queue
import tkinter as tk
import customtkinter as ctk
from PIL import Image
import requests

# Set theme and appearance
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def _enable_kill_on_exit():
    """Windows Only: Ensure subprocesses die when the main process dies."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        from ctypes import wintypes
        job = ctypes.windll.kernel32.CreateJobObjectW(None, None)
        
        # JOBOBJECT_EXTENDED_LIMIT_INFORMATION
        class IO_COUNTERS(ctypes.Structure):
            _fields_ = [('ReadOperationCount', ctypes.c_ulonglong), ('WriteOperationCount', ctypes.c_ulonglong), 
                       ('OtherOperationCount', ctypes.c_ulonglong), ('ReadTransferCount', ctypes.c_ulonglong), 
                       ('WriteTransferCount', ctypes.c_ulonglong), ('OtherTransferCount', ctypes.c_ulonglong)]
        class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [('PerProcessUserTimeLimit', ctypes.c_longlong), ('PerJobUserTimeLimit', ctypes.c_longlong), 
                       ('LimitFlags', ctypes.c_ulong), ('MinimumWorkingSetSize', ctypes.c_size_t), 
                       ('MaximumWorkingSetSize', ctypes.c_size_t), ('ActiveProcessLimit', ctypes.c_ulong), 
                       ('Affinity', ctypes.c_size_t), ('PriorityClass', ctypes.c_ulong), 
                       ('SchedulingClass', ctypes.c_ulong)]
        class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [('BasicLimitInformation', JOBOBJECT_BASIC_LIMIT_INFORMATION), ('IoInfo', IO_COUNTERS), 
                       ('ProcessMemoryLimit', ctypes.c_size_t), ('JobMemoryLimit', ctypes.c_size_t), 
                       ('PeakProcessMemoryUsed', ctypes.c_size_t), ('PeakJobMemoryUsed', ctypes.c_size_t)]
        
        # 0x2000 = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        job_info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        job_info.BasicLimitInformation.LimitFlags = 0x2000
        
        ctypes.windll.kernel32.SetInformationJobObject(
            job, 9, ctypes.byref(job_info), ctypes.sizeof(job_info)
        )
        ctypes.windll.kernel32.AssignProcessToJobObject(job, ctypes.windll.kernel32.GetCurrentProcess())
        return job # Keep reference alive
    except Exception as e:
        print(f"Failed to enable job object: {e}")
        return None

def ensure_firewall_rule(log_callback=print):
    """
    Ensure Windows Firewall allows port 8000.
    Creates rule if it doesn't exist. Requires admin for first-time setup.
    """
    RULE_NAME = "MOD-EVAC-MS Backend"
    PORT = 8000
    
    # Check if rule already exists
    try:
        result = subprocess.run(
            ["netsh", "advfirewall", "firewall", "show", "rule", f"name={RULE_NAME}"],
            capture_output=True, text=True, timeout=10
        )
        if RULE_NAME in result.stdout:
            log_callback(f"[Firewall] Rule '{RULE_NAME}' already exists")
            return True
    except Exception as e:
        log_callback(f"[Firewall] Check failed: {e}")
    
    # Try to create rule (needs admin)
    try:
        result = subprocess.run(
            [
                "netsh", "advfirewall", "firewall", "add", "rule",
                f"name={RULE_NAME}",
                "dir=in",
                "action=allow",
                "protocol=tcp",
                f"localport={PORT}"
            ],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            log_callback(f"[Firewall] Successfully added rule for port {PORT}")
            return True
        else:
            # Needs elevation - request UAC
            log_callback("[Firewall] Needs admin privileges, requesting elevation...")
            return _request_admin_firewall(RULE_NAME, PORT, log_callback)
    except Exception as e:
        log_callback(f"[Firewall] Failed to add rule: {e}")
        return False


def _request_admin_firewall(rule_name, port, log_callback=print):
    """Request UAC elevation to add firewall rule and wait for completion."""
    import ctypes
    import ctypes.wintypes
    
    # Marker file to confirm completion
    marker_path = os.path.join(os.environ.get('TEMP', '.'), 'modevac_firewall_done.txt')
    if os.path.exists(marker_path):
        os.remove(marker_path)
    
    # Create a temporary batch script that creates a marker when done
    script_content = f'''@echo off
netsh advfirewall firewall add rule name="{rule_name}" dir=in action=allow protocol=tcp localport={port}
if %errorlevel% equ 0 (
    echo SUCCESS > "{marker_path}"
    echo Firewall rule added successfully!
) else (
    echo FAILED > "{marker_path}"
    echo Failed to add firewall rule.
)
timeout /t 2 >nul
'''
    
    script_path = os.path.join(os.environ.get('TEMP', '.'), 'modevac_firewall.bat')
    try:
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        # Use ShellExecuteEx to run and wait
        # SEE_MASK_NOCLOSEPROCESS = 0x00000040
        class SHELLEXECUTEINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.wintypes.DWORD),
                ("fMask", ctypes.c_ulong),
                ("hwnd", ctypes.wintypes.HANDLE),
                ("lpVerb", ctypes.c_wchar_p),
                ("lpFile", ctypes.c_wchar_p),
                ("lpParameters", ctypes.c_wchar_p),
                ("lpDirectory", ctypes.c_wchar_p),
                ("nShow", ctypes.c_int),
                ("hInstApp", ctypes.wintypes.HINSTANCE),
                ("lpIDList", ctypes.c_void_p),
                ("lpClass", ctypes.c_wchar_p),
                ("hkeyClass", ctypes.wintypes.HKEY),
                ("dwHotKey", ctypes.wintypes.DWORD),
                ("hIconOrMonitor", ctypes.wintypes.HANDLE),
                ("hProcess", ctypes.wintypes.HANDLE),
            ]
        
        sei = SHELLEXECUTEINFO()
        sei.cbSize = ctypes.sizeof(sei)
        sei.fMask = 0x00000040  # SEE_MASK_NOCLOSEPROCESS
        sei.hwnd = None
        sei.lpVerb = "runas"
        sei.lpFile = script_path
        sei.lpParameters = None
        sei.lpDirectory = None
        sei.nShow = 1  # SW_SHOWNORMAL
        sei.hInstApp = None
        sei.hProcess = None
        
        if ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(sei)):
            log_callback("[Firewall] Waiting for User Confirmation...")
            # Wait for the process to complete (max 30 seconds)
            if sei.hProcess:
                ctypes.windll.kernel32.WaitForSingleObject(sei.hProcess, 30000)
                ctypes.windll.kernel32.CloseHandle(sei.hProcess)
            
            # Check marker file
            time.sleep(0.5)
            if os.path.exists(marker_path):
                with open(marker_path, 'r') as f:
                    result = f.read().strip()
                os.remove(marker_path)
                if result == "SUCCESS":
                    print(f"[Firewall] Successfully added rule for port {port}")
                    return True
        
        print("[Firewall] UAC was cancelled or failed")
        return False
        
    except Exception as e:
        print(f"[Firewall] UAC request failed: {e}")
        return False



class QueueHandler(logging.Handler):
    """Custom logging handler to send logs to a queue for GUI display"""
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        msg = self.format(record)
        self.log_queue.put(msg)

class NexoraLauncher(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("NEXORA OPS | Command Center Launcher")
        self.geometry("900x550")
        
        # Application State
        self.server_process = None
        self.is_running = False
        self.local_ip = self._get_local_ip()
        self.pairing_code = "--- ---"
        self.log_queue = queue.Queue()
        
        self._setup_ui()
        self.log("NEXORA OS BOOTSTRAP COMPLETE.")
        self.log(f"DETECTED LOCAL ENDPOINT: {self.local_ip}")
        
        # Start log consumer
        self._consume_logs()
        
        # Shutdown Hooks
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        import atexit
        atexit.register(self.cleanup)
        
        # Windows Job Object (Auto-Kill Children)
        _enable_kill_on_exit()

    def cleanup(self):
        """Force cleanup of child processes."""
        self.is_running = False
        if self.server_process:
            try:
                self.server_process.terminate()
                # Give it a moment to die cleanly
                self.server_process.wait(timeout=1)
            except:
                try: 
                   self.server_process.kill()
                except:
                   pass
            self.server_process = None

    def on_closing(self):
        """Handle window close event."""
        self.cleanup()
        self.quit()
        self.destroy()

    def _get_local_ip(self):
        """Get local IP address with multiple fallback methods."""
        # Method 1: UDP socket trick (most reliable)
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(2)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            if ip and ip != "0.0.0.0":
                return ip
        except Exception:
            pass
        
        # Method 2: Get all network interfaces
        try:
            hostname = socket.gethostname()
            addresses = socket.getaddrinfo(hostname, None, socket.AF_INET)
            for addr in addresses:
                ip = addr[4][0]
                if ip and not ip.startswith("127."):
                    return ip
        except Exception:
            pass
        
        # Method 3: Hostname resolution
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            pass
        
        return "127.0.0.1"


    def _setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # SIDEPANEL
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar.grid_rowconfigure(7, weight=1)  # Push empty space to bottom

        logo_label = ctk.CTkLabel(self.sidebar, text="NEXORA", font=ctk.CTkFont(size=24, weight="bold", family="Orbitron"))
        logo_label.grid(row=0, column=0, padx=20, pady=(20, 5))
        
        subtitle = ctk.CTkLabel(self.sidebar, text="MOD-EVAC SYSTEM v1.0", font=ctk.CTkFont(size=11, family="Consolas"))
        subtitle.grid(row=1, column=0, padx=20, pady=(0, 20))

        # STATUS INDICATOR
        self.status_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.status_frame.grid(row=2, column=0, padx=20, pady=5)
        
        self.status_dot = ctk.CTkLabel(self.status_frame, text="●", text_color="#ef4444", font=ctk.CTkFont(size=18))
        self.status_dot.pack(side="left", padx=5)
        
        self.status_text = ctk.CTkLabel(self.status_frame, text="STATION OFFLINE", font=ctk.CTkFont(weight="bold", size=13))
        self.status_text.pack(side="left")

        # MAIN CONTROL BUTTON
        self.control_btn = ctk.CTkButton(self.sidebar, text="START COMMAND", height=40, font=ctk.CTkFont(weight="bold"),
                                        command=self.toggle_server, fg_color="#3b82f6", hover_color="#2563eb")
        self.control_btn.grid(row=3, column=0, padx=20, pady=(15, 20))

        # QUICK LINKS SECTION
        ctk.CTkLabel(self.sidebar, text="STATION LINKS", font=ctk.CTkFont(size=10, weight="bold"), text_color="#64748b").grid(row=4, column=0, padx=20, pady=(10, 5), sticky="w")
        
        self.admin_btn = ctk.CTkButton(self.sidebar, text="ADMIN DASHBOARD", height=32, state="disabled", 
                                       command=lambda: webbrowser.open("http://localhost:8000"),
                                       fg_color="#1e293b", hover_color="#334155")
        self.admin_btn.grid(row=5, column=0, padx=20, pady=(0, 5), sticky="ew")
        
        self.public_btn = ctk.CTkButton(self.sidebar, text="PUBLIC PORTAL", height=32, state="disabled",
                                        command=lambda: webbrowser.open("http://localhost:8000/public"),
                                        fg_color="#1e293b", hover_color="#334155")
        self.public_btn.grid(row=6, column=0, padx=20, pady=(0, 10), sticky="ew")


        # MAIN CONTENT
        self.main = ctk.CTkFrame(self, fg_color="transparent")
        self.main.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_rowconfigure(2, weight=1)

        # INFOCARDS (TOP)
        info_row = ctk.CTkFrame(self.main, fg_color="transparent")
        info_row.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        info_row.grid_columnconfigure((0, 1), weight=1)

        # IP ADDRESS CARD
        ip_card = ctk.CTkFrame(info_row, border_width=1, border_color="#1e293b")
        ip_card.grid(row=0, column=0, padx=(0, 10), sticky="nsew")
        ctk.CTkLabel(ip_card, text="NETWORK ENDPOINT", font=ctk.CTkFont(size=10, weight="bold"), text_color="#10b981").pack(pady=(10, 0))
        self.ip_display = ctk.CTkLabel(ip_card, text=self.local_ip, font=ctk.CTkFont(size=28, weight="bold"))
        self.ip_display.pack(pady=10)

        # PAIRING CODE CARD
        code_card = ctk.CTkFrame(info_row, border_width=1, border_color="#1e293b")
        code_card.grid(row=0, column=1, padx=(10, 0), sticky="nsew")
        ctk.CTkLabel(code_card, text="PUBLIC PAIRING CODE", font=ctk.CTkFont(size=10, weight="bold"), text_color="#f59e0b").pack(pady=(10, 0))
        self.code_display = ctk.CTkLabel(code_card, text=self.pairing_code, font=ctk.CTkFont(size=28, weight="bold"))
        self.code_display.pack(pady=10)

        # LOGS SECTION
        log_frame = ctk.CTkFrame(self.main, border_width=1, border_color="#1e293b")
        log_frame.grid(row=1, column=0, sticky="nsew", pady=10)
        log_frame.grid_rowconfigure(1, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(log_frame, text="SYSTEM INTELLIGENCE LOGS", font=ctk.CTkFont(size=11, weight="bold")).grid(row=0, column=0, padx=20, pady=10, sticky="w")
        
        self.log_area = ctk.CTkTextbox(log_frame, font=("Consolas", 11), text_color="#10b981", fg_color="#0a0a0a")
        self.log_area.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")

    def log(self, text):
        """Thread-safe logging: pushes message to queue."""
        self.log_queue.put(f"SYS:{text}")
    
    def _update_log_ui(self, text):
        """Actual UI update (MUST be called from main thread only)."""
        ts = time.strftime("[%H:%M:%S]")
        self.log_area.insert("end", f"{ts} {text}\n")
        self.log_area.see("end")
    
    def _consume_logs(self):
        """Poll the queue for new log messages and update UI on main thread."""
        try:
            while True:
                msg = self.log_queue.get_nowait()
                
                # System messages (explicitly logged)
                if msg.startswith("SYS:"):
                    self._update_log_ui(msg[4:])
                    continue
                
                # Server logs (filtered)
                if "GET /" in msg or "WebSocket" in msg or "Uvicorn running" in msg or "Application startup complete" in msg:
                    self._update_log_ui(msg.strip())
                
                if "Uvicorn running" in msg or "Application startup complete" in msg:
                    self._on_server_ready()
        except queue.Empty:
            pass
        finally:
            self.after(100, self._consume_logs)

    def toggle_server(self):
        if not self.is_running:
            self.start_server()
        else:
            self.stop_server()

    def start_server(self):
        # 1. Nuclear Cleanup: Kill any zombies holding port 8000
        self._kill_zombies()
        
        self.is_running = True
        self.control_btn.configure(text="SHUTDOWN STATION", fg_color="#ef4444", hover_color="#dc2626")
        self.status_dot.configure(text_color="#f59e0b")
        self.status_text.configure(text="INITIALIZING...")
        
        # Start server thread (Firewall check happens inside)
        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()
        
        # Start access code updater
        self.updater_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.updater_thread.start()

    def _kill_zombies(self):
        """Force kill any process using port 8000 to prevent 'Port in use' errors."""
        try:
            if sys.platform == "win32":
                # Find PID using netstat
                cmd = "netstat -ano | findstr :8000"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.stdout:
                    for line in result.stdout.strip().split('\n'):
                        parts = line.split()
                        if len(parts) > 4:
                            pid = parts[-1]
                            if pid != str(os.getpid()):
                                self.log(f"Killing zombie process {pid} on port 8000...")
                                subprocess.run(f"taskkill /F /PID {pid}", shell=True)
            else:
                subprocess.run("fuser -k 8000/tcp", shell=True)
        except Exception as e:
            self.log(f"ZOMBIE CLEANUP ERROR: {e}")

    def stop_server(self):
        # Shutdown logic depends on mode
        if getattr(sys, 'frozen', False):
            # In frozen mode, we can't easily kill the thread running uvicorn cleanly without a shutdown signal
            # For now, we set flag to False and let user exit app or restart.
            # Ideally, proper server shutdown is needed, but thread killing is hard.
            # We will just update UI and stop loops.
            self.log("Stopping in-process server (App restart required to fully kill backend threads)")
        else:
            if self.server_process:
                self.log("Terminating server process...")
                try:
                    self.server_process.terminate()
                    self.server_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.log("Server unresponsive, forcing kill...")
                    self.server_process.kill()
                except Exception as e:
                    self.log(f"Error stopping server: {e}")
                
                self.server_process = None
        
        self.is_running = False
        self.control_btn.configure(text="START COMMAND", fg_color="#3b82f6", hover_color="#2563eb")
        self.status_dot.configure(text_color="#ef4444")
        self.status_text.configure(text="STATION OFFLINE")
        self.admin_btn.configure(state="disabled")
        self.public_btn.configure(state="disabled")
        self.pairing_code = "--- ---"
        self.code_display.configure(text=self.pairing_code)
        self.log("NEXORA STATION SHUTDOWN COMPLETE.")

    def _run_server(self):
        # 0. Check Firewall (in background thread)
        self.log("Checking firewall configuration...")
        ensure_firewall_rule(self.log)

        if getattr(sys, 'frozen', False):
             # FROZEN MODE: Run In-Process
             try:
                 self.log("Running in FROZEN mode (In-Process Server)")
                 
                 # 1. Setup Logging
                 handler = QueueHandler(self.log_queue)
                 formatter = logging.Formatter('%(levelname)s: %(message)s')
                 handler.setFormatter(formatter)
                 
                 # Attach to connection watchers
                 logger = logging.getLogger("uvicorn")
                 logger.addHandler(handler)
                 logger.setLevel(logging.INFO)
                 
                 # 2. Import Server dynamically
                 # backend is bundled in the same dir or in _MEIPASS/backend
                 backend_path = resource_path("backend")
                 if backend_path not in sys.path:
                     sys.path.insert(0, backend_path)
                 
                 import uvicorn
                 from server import app as fastapi_app
                 
                 # 3. Run Server
                 # We disable signals to prevent conflicts with GUI main thread
                 uvicorn.run(fastapi_app, host="0.0.0.0", port=8000, log_config=None)
                 
             except Exception as e:
                 self.log(f"CRITICAL SERVER FAILURE: {e}")
                 import traceback
                 self.log(traceback.format_exc())
        else:
            # DEV MODE: Run Subprocess
            try:
                cwd = resource_path("backend")
                python_exe = sys.executable
                
                self.log(f"Starting server from: {cwd}")
                
                # Verify backend exists
                if not os.path.exists(cwd):
                     self.log(f"ERROR: Backend directory not found at {cwd}")
                     return

                cmd = [python_exe, "-u", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
                
                self.server_process = subprocess.Popen(
                    cmd, 
                    cwd=cwd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.STDOUT, 
                    text=True,
                    encoding="utf-8", 
                    errors="replace",
                    bufsize=1  # Line buffered
                )

                self.log("Server process started...")
                
                for line in iter(self.server_process.stdout.readline, ""):
                    if not self.is_running: break
                    # Push to queue for consistency
                    self.log_queue.put(line)
                
                # If we get here, the process has exited
                if self.is_running:
                    ret_code = self.server_process.wait()
                    self.log(f"CRITICAL: Backend process exited with code {ret_code}")
                    self.after(0, self.stop_server)
            except Exception as e:
                self.log(f"CRITICAL LAUNCH ERROR: {e}")
                import traceback
                self.log(traceback.format_exc())

    def _on_server_ready(self):
        self.status_dot.configure(text_color="#10b981")
        self.status_text.configure(text="STATION ACTIVE")
        self.admin_btn.configure(state="normal")
        self.public_btn.configure(state="normal")
        self.log("WEBSITE ACCESSIBLE AT PORT 8000")

    def _update_loop(self):
        while self.is_running:
            try:
                # 1. Real-time IP Monitoring: Check if network changed
                current_ip = self._get_local_ip()
                if current_ip != self.local_ip:
                    old_ip = self.local_ip
                    self.local_ip = current_ip
                    self.log(f"NETWORK CHANGE DETECTED: {old_ip} -> {current_ip}")
                    self.log("IMPORTANT: Please update your Camera settings with the new IP!")
                    self.after(0, lambda: self.ip_display.configure(text=self.local_ip, text_color="#ef4444"))
                else:
                    self.after(0, lambda: self.ip_display.configure(text_color="white"))

                # 2. Fetch pairing code from local API
                resp = requests.get("http://localhost:8000/api/access_code", timeout=2)
                if resp.status_code == 200:
                    code = resp.json().get('code', '--- ---')
                    self.pairing_code = code
                    self.after(0, lambda: self.code_display.configure(text=self.pairing_code))
            except Exception as e:
                pass
            time.sleep(10)

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    app = NexoraLauncher()
    app.mainloop()
