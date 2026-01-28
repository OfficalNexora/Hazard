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
        self.geometry("900x650")
        
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

    def _get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return socket.gethostbyname(socket.gethostname())

    def _setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # SIDEPANEL
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar.grid_rowconfigure(5, weight=1)

        logo_label = ctk.CTkLabel(self.sidebar, text="NEXORA", font=ctk.CTkFont(size=24, weight="bold", family="Orbitron"))
        logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        subtitle = ctk.CTkLabel(self.sidebar, text="MOD-EVAC SYSTEM v1.0", font=ctk.CTkFont(size=11, family="Consolas"))
        subtitle.grid(row=1, column=0, padx=20, pady=(0, 30))

        # STATUS INDICATOR
        self.status_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.status_frame.grid(row=2, column=0, padx=20, pady=10)
        
        self.status_dot = ctk.CTkLabel(self.status_frame, text="●", text_color="#ef4444", font=ctk.CTkFont(size=18))
        self.status_dot.pack(side="left", padx=5)
        
        self.status_text = ctk.CTkLabel(self.status_frame, text="STATION OFFLINE", font=ctk.CTkFont(weight="bold", size=13))
        self.status_text.pack(side="left")

        # MAIN CONTROL BUTTON
        self.control_btn = ctk.CTkButton(self.sidebar, text="START COMMAND", height=40, font=ctk.CTkFont(weight="bold"),
                                        command=self.toggle_server, fg_color="#3b82f6", hover_color="#2563eb")
        self.control_btn.grid(row=3, column=0, padx=20, pady=20)

        # QUICK LINKS SECTION
        ctk.CTkLabel(self.sidebar, text="STATION LINKS", font=ctk.CTkFont(size=10, weight="bold"), text_color="#64748b").grid(row=4, column=0, padx=20, pady=(20, 0), sticky="w")
        
        self.admin_btn = ctk.CTkButton(self.sidebar, text="ADMIN DASHBOARD", height=32, state="disabled", 
                                       command=lambda: webbrowser.open("http://localhost:8000"),
                                       fg_color="#1e293b", hover_color="#334155")
        self.admin_btn.grid(row=5, column=0, padx=20, pady=5)
        
        self.public_btn = ctk.CTkButton(self.sidebar, text="PUBLIC PORTAL", height=32, state="disabled",
                                        command=lambda: webbrowser.open(f"http://{self.local_ip}:8000/public"),
                                        fg_color="#1e293b", hover_color="#334155")
        self.public_btn.grid(row=6, column=0, padx=20, pady=5)

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
        ip_card = ctk.CTkFrame(info_row, border_width=1, border_color="#ffffff10")
        ip_card.grid(row=0, column=0, padx=(0, 10), sticky="nsew")
        ctk.CTkLabel(ip_card, text="NETWORK ENDPOINT", font=ctk.CTkFont(size=10, weight="bold"), text_color="#10b981").pack(pady=(10, 0))
        self.ip_display = ctk.CTkLabel(ip_card, text=self.local_ip, font=ctk.CTkFont(size=28, weight="bold"))
        self.ip_display.pack(pady=10)

        # PAIRING CODE CARD
        code_card = ctk.CTkFrame(info_row, border_width=1, border_color="#ffffff10")
        code_card.grid(row=0, column=1, padx=(10, 0), sticky="nsew")
        ctk.CTkLabel(code_card, text="PUBLIC PAIRING CODE", font=ctk.CTkFont(size=10, weight="bold"), text_color="#f59e0b").pack(pady=(10, 0))
        self.code_display = ctk.CTkLabel(code_card, text=self.pairing_code, font=ctk.CTkFont(size=28, weight="bold"))
        self.code_display.pack(pady=10)

        # LOGS SECTION
        log_frame = ctk.CTkFrame(self.main, border_width=1, border_color="#ffffff05")
        log_frame.grid(row=1, column=0, sticky="nsew", pady=10)
        log_frame.grid_rowconfigure(1, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(log_frame, text="SYSTEM INTELLIGENCE LOGS", font=ctk.CTkFont(size=11, weight="bold")).grid(row=0, column=0, padx=20, pady=10, sticky="w")
        
        self.log_area = ctk.CTkTextbox(log_frame, font=("Consolas", 11), text_color="#10b981", fg_color="#0a0a0a")
        self.log_area.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")

    def log(self, text):
        ts = time.strftime("[%H:%M:%S]")
        self.log_area.insert("end", f"{ts} {text}\n")
        self.log_area.see("end")
    
    def _consume_logs(self):
        """Poll the queue for new log messages."""
        try:
            while True:
                msg = self.log_queue.get_nowait()
                if "GET /" in msg or "WebSocket" in msg or "Uvicorn running" in msg:
                    self.log(msg.strip())
                
                if "Uvicorn running" in msg:
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
        self.is_running = True
        self.control_btn.configure(text="SHUTDOWN STATION", fg_color="#ef4444", hover_color="#dc2626")
        self.status_dot.configure(text_color="#f59e0b")
        self.status_text.configure(text="INITIALIZING...")
        
        # Start server thread
        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()
        
        # Start access code updater
        self.updater_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.updater_thread.start()

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
                self.server_process.terminate()
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
            cwd = resource_path("backend")
            python_exe = sys.executable
            
            cmd = [python_exe, "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
            
            self.server_process = subprocess.Popen(
                cmd, 
                cwd=cwd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                text=True,
                bufsize=1
            )

            for line in iter(self.server_process.stdout.readline, ""):
                if not self.is_running: break
                # Push to queue for consistency
                self.log_queue.put(line)

    def _on_server_ready(self):
        self.status_dot.configure(text_color="#10b981")
        self.status_text.configure(text="STATION ACTIVE")
        self.admin_btn.configure(state="normal")
        self.public_btn.configure(state="normal")
        self.log("WEBSITE ACCESSIBLE AT PORT 8000")

    def _update_loop(self):
        while self.is_running:
            try:
                # Fetch pairing code from local API
                resp = requests.get("http://localhost:8000/api/access_code", timeout=2)
                if resp.status_code == 200:
                    code = resp.json().get('code', '--- ---')
                    self.pairing_code = code
                    self.after(0, lambda: self.code_display.configure(text=self.pairing_code))
            except:
                pass
            time.sleep(10)

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    app = NexoraLauncher()
    app.mainloop()
