import argparse
import json
import socket
import threading
import time
import sys
import os
import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox
from typing import Optional, List
import struct
import base64
import multiprocessing

# Optional dependencies
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False

# =============================================================================
# CONFIGURATION CONSTANTS
# =============================================================================
DEFAULT_SERVER_PORT = 8001
DEFAULT_DISCOVERY_PORT = 8002
HEARTBEAT_INTERVAL = 5

# Set theme
# I chose a dark theme by default to reduce eye strain during long monitoring sessions in dim control rooms.
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# =============================================================================
# MODERN GUI APPLICATION
# =============================================================================
class WorkerGUI(ctk.CTk):
    """
    I designed this GUI to provide immediate visual feedback on the worker's status.
    It serves as a "headless" node monitor that can also be controlled manually if needed.
    """
    def __init__(self):
        super().__init__()

        self.title("MOD-EVAC-MS | Intelligence Worker")
        self.geometry("800x600")
        
        # Worker State
        self.worker = None
        self.is_connected = False
        
        self._setup_ui()
        self._load_config()
        
    def _setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar.grid_rowconfigure(4, weight=1)

        logo_label = ctk.CTkLabel(self.sidebar, text="MOD-EVAC", font=ctk.CTkFont(size=20, weight="bold"))
        logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        subtitle = ctk.CTkLabel(self.sidebar, text="AI Node v1.0", font=ctk.CTkFont(size=12))
        subtitle.grid(row=1, column=0, padx=20, pady=(0, 20))

        self.status_box = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.status_box.grid(row=2, column=0, padx=10, pady=10)
        
        self.status_dot = ctk.CTkLabel(self.status_box, text="●", text_color="#ff4444", font=ctk.CTkFont(size=14))
        self.status_dot.pack(side="left", padx=5)
        
        self.status_text = ctk.CTkLabel(self.status_box, text="OFFLINE", font=ctk.CTkFont(weight="bold"))
        self.status_text.pack(side="left")

        self.start_btn = ctk.CTkButton(self.sidebar, text="START WORKER", command=self.toggle_worker, 
                                       fg_color="#10b981", hover_color="#059669")
        self.start_btn.grid(row=3, column=0, padx=20, pady=20)

        # Appearance Settings
        self.appearance_mode_label = ctk.CTkLabel(self.sidebar, text="Theme:", anchor="w")
        self.appearance_mode_label.grid(row=5, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_optionemenu = ctk.CTkOptionMenu(self.sidebar, values=["Light", "Dark", "System"],
                                                               command=self.change_appearance_mode)
        self.appearance_mode_optionemenu.grid(row=6, column=0, padx=20, pady=(10, 20))
        self.appearance_mode_optionemenu.set("Dark")

        # Main Content
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(2, weight=1)

        # Row 1: Config Cards
        row1 = ctk.CTkFrame(self.main_container, fg_color="transparent")
        row1.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        row1.grid_columnconfigure((0, 1), weight=1)

        # Network Config Card
        net_card = ctk.CTkFrame(row1)
        net_card.grid(row=0, column=0, padx=(0, 10), sticky="nsew")
        ctk.CTkLabel(net_card, text="Network Configuration", font=ctk.CTkFont(weight="bold")).pack(pady=10)
        
        self.name_var = tk.StringVar(value=f"Worker-{socket.gethostname()}")
        ctk.CTkLabel(net_card, text="Worker Name:", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=20)
        ctk.CTkEntry(net_card, textvariable=self.name_var).pack(fill="x", padx=20, pady=(0, 10))
        
        self.ip_var = tk.StringVar(value="auto")
        ctk.CTkLabel(net_card, text="Manual Server IP:", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=20)
        ctk.CTkEntry(net_card, textvariable=self.ip_var, placeholder_text="auto").pack(fill="x", padx=20, pady=(0, 10))

        # AI Config Card
        ai_card = ctk.CTkFrame(row1)
        ai_card.grid(row=0, column=1, padx=(10, 0), sticky="nsew")
        ctk.CTkLabel(ai_card, text="Artificial Intelligence", font=ctk.CTkFont(weight="bold")).pack(pady=10)
        
        self.model_var = tk.StringVar(value="yolov8n.pt")
        ctk.CTkLabel(ai_card, text="Active Model:", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=20)
        self.model_menu = ctk.CTkOptionMenu(ai_card, values=["yolov8n.pt", "yolov8s.pt", "custom_hazard.pt"],
                                           variable=self.model_var)
        self.model_menu.pack(fill="x", padx=20, pady=(0, 10))
        
        # Dual AI Selector (New)
        ctk.CTkLabel(ai_card, text="Secondary Model (Dual AI):", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=20)
        self.model_var_2 = tk.StringVar(value="None")
        self.model_menu_2 = ctk.CTkOptionMenu(ai_card, values=["None", "yolov8n.pt", "yolov8s.pt", "custom_hazard.pt"],
                                             variable=self.model_var_2)
        self.model_menu_2.pack(fill="x", padx=20, pady=(0, 10))

        # Row 2: Stats Dashboard
        stats_frame = ctk.CTkFrame(self.main_container)
        stats_frame.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        stats_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.fps_stat = self._create_stat_box(stats_frame, 0, "INFERENCE FPS", "0.0")
        self.det_stat = self._create_stat_box(stats_frame, 1, "TOTAL DETECTIONS", "0")
        self.lat_stat = self._create_stat_box(stats_frame, 2, "LATENCY (ms)", "0")

        # Row 3: Scrolled Logs
        log_container = ctk.CTkFrame(self.main_container)
        log_container.grid(row=2, column=0, sticky="nsew")
        ctk.CTkLabel(log_container, text="SYSTEM STATUS LOGS", font=ctk.CTkFont(size=12, weight="bold")).pack(pady=10)
        
        self.log_area = ctk.CTkTextbox(log_container, font=("Consolas", 11), text_color="#10b981", fg_color="#000000")
        self.log_area.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _create_stat_box(self, parent, col, title, value):
        box = ctk.CTkFrame(parent, fg_color="#252525")
        box.grid(row=0, column=col, padx=5, pady=5, sticky="nsew")
        ctk.CTkLabel(box, text=title, font=ctk.CTkFont(size=10, weight="bold"), text_color="#94a3b8").pack(pady=(5, 0))
        label = ctk.CTkLabel(box, text=value, font=ctk.CTkFont(size=24, weight="bold"))
        label.pack(pady=(0, 5))
        return label

    def log(self, message):
        timestamp = time.strftime("[%H:%M:%S] ")
        self.log_area.insert("end", f"{timestamp}{message}\n")
        self.log_area.see("end")

    def _load_config(self):
        if not YOLO_AVAILABLE:
            self.log("CRITICAL: Ultralytics not found! AI functionality disabled.")
            self.model_menu.configure(state="disabled")
        if not CV2_AVAILABLE:
            self.log("WARNING: OpenCV not found! Physical frame processing disabled.")

    def change_appearance_mode(self, new_mode):
        ctk.set_appearance_mode(new_mode)

    def toggle_worker(self):
        if self.worker and self.worker.running:
            self.stop_worker()
        else:
            self.start_worker()

    def start_worker(self):
        name = self.name_var.get()
        model = self.model_var.get()
        model_2 = self.model_var_2.get()
        server_ip = self.ip_var.get()
        
        self.worker = WorkerApp(self, name, model, server_ip if server_ip != 'auto' else None, model_path_2=model_2)
        self.worker_thread = threading.Thread(target=self.worker.start, daemon=True)
        self.worker_thread.start()
        
        self.start_btn.configure(text="STOP WORKER", fg_color="#ef4444", hover_color="#dc2626")
        self.status_dot.configure(text_color="#f59e0b")
        self.status_text.configure(text="STARTING...")
        self.log(f"Initializing connection to backend via {server_ip}...")

    def stop_worker(self):
        if self.worker:
            self.worker.stop()
        self.start_btn.configure(text="START WORKER", fg_color="#10b981", hover_color="#059669")
        self.status_dot.configure(text_color="#ff4444")
        self.status_text.configure(text="OFFLINE")
        self.log("Worker instance terminated.")
        
    def update_status(self, connected):
        self.is_connected = connected
        if connected:
            self.status_dot.configure(text_color="#10b981")
            self.status_text.configure(text="CONNECTED")
        else:
            self.status_dot.configure(text_color="#f59e0b")
            self.status_text.configure(text="RECONNECTING...")

    def update_stats(self, fps, detections, latency):
        self.fps_stat.configure(text=f"{fps:.1f}")
        self.det_stat.configure(text=f"{detections}")
        self.lat_stat.configure(text=f"{latency:.0f}")

# =============================================================================
# WORKER CORE LOGIC
# =============================================================================
class WorkerApp:
    """
    I implemented this class to handle the heavy lifting of AI inference.
    It runs in a separate thread to ensure the GUI remains responsive even when processing 4K video frames.
    """
    def __init__(self, gui, name, model_path, server_ip=None, model_path_2="None"):
        self.gui = gui
        self.name = name
        self.model_path = model_path
        self.model_path_2 = model_path_2
        self.server_ip = server_ip
        
        self.worker_id = f"{name}_{int(time.time())}"
        self.running = False
        self.connected = False
        self.socket = None
        self.model = None
        self.model_2 = None
        
        self.frames_processed = 0
        self.detections_count = 0
        self.start_time = time.time()
        
        self.hazard_classes = [
            "Fire", "Smoke", "Flood", "Falling Debris",
            "Landslide", "Explosion", "Collapsed Structure", "Industrial Accident"
        ]

    def log(self, msg):
        self.gui.after(0, self.gui.log, msg)

    def start(self):
        self.running = True
        
        # 1. Load Custom Models
        if YOLO_AVAILABLE:
            try:
                self.log(f"Loading Primary Model: {self.model_path}")
                self.model = YOLO(self.model_path)
                
                if self.model_path_2 and self.model_path_2 != "None":
                    self.log(f"Loading Secondary Model: {self.model_path_2}")
                    self.model_2 = YOLO(self.model_path_2)
                
                self.log("AI Engine status: OPTIMAL (Dual-Core Ready)")
            except Exception as e:
                self.log(f"Engine failure: {e}")
                self.running = False
                return

        # 2. Discover/Connect Server
        if not self.server_ip:
            self.log("Broadcasting discovery packets (UDP 8002)...")
            self.server_ip = self._discover()
        
        if self.server_ip:
            self._connect()
        else:
            self.log("Handshake failed: No server found.")
            self.running = False
            self.gui.after(0, self.gui.stop_worker)
            return

        # 3. Main Loop
        if self.connected:
            self._main_loop()

    def _discover(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(5)
        try:
            sock.bind(('', DEFAULT_DISCOVERY_PORT))
            data, addr = sock.recvfrom(1024)
            msg = json.loads(data.decode())
            if msg.get('type') == 'server_announce':
                ip = msg.get('ip') or addr[0]
                self.log(f"Protocol match: Server detected at {ip}")
                return ip
        except Exception as e:
            self.log(f"Port scan error: {e}")
        finally:
            sock.close()
        return None

    def _connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server_ip, DEFAULT_SERVER_PORT))
            
            # Register
            reg = {
                "type": "register",
                "worker_id": self.worker_id,
                "name": self.name,
                "model": self.model_path
            }
            self._send(reg)
            self.connected = True
            self.gui.after(0, self.gui.update_status, True)
            self.log(f"Tunnel established: {self.server_ip}")
        except Exception as e:
            self.log(f"Socket error: {e}")
            self.connected = False

    def _send(self, msg):
        if not self.socket: return
        data = json.dumps(msg).encode()
        self.socket.sendall(struct.pack('>I', len(data)) + data)

    def _receive(self):
        if not self.socket: return None
        try:
            len_data = self.socket.recv(4)
            if not len_data: return None
            length = struct.unpack('>I', len_data)[0]
            data = b''
            while len(data) < length:
                chunk = self.socket.recv(length - len(data))
                if not chunk: break
                data += chunk
            return json.loads(data.decode())
        except:
            return None

    def _main_loop(self):
        last_heartbeat = 0
        self.gui.after(0, self.gui.update_status, True)
        
        while self.running and self.connected:
            try:
                # Heartbeat
                if time.time() - last_heartbeat > HEARTBEAT_INTERVAL:
                    stats = {
                        "fps": self.frames_processed / (time.time() - self.start_time) if (time.time() - self.start_time) > 0 else 0,
                        "detections": self.detections_count
                    }
                    self._send({"type": "heartbeat", "worker_id": self.worker_id, "stats": stats})
                    last_heartbeat = time.time()
                    
                # Check for tasks (blocking with timeout)
                self.socket.settimeout(0.5)
                task = self._receive()
                if task:
                    if task.get('type') == 'inference_task':
                        self._do_inference(task)
                
                # Update GUI Stats
                elapsed = time.time() - self.start_time
                fps = self.frames_processed / elapsed if elapsed > 0 else 0
                self.gui.after(0, self.gui.update_stats, fps, self.detections_count, 0)
                
            except socket.timeout:
                continue
            except Exception as e:
                self.log(f"Connection lost: {e}")
                self.connected = False
                self.gui.after(0, self.gui.update_status, False)
                break

    def _do_inference(self, task):
        if not self.model or not CV2_AVAILABLE: return
        try:
            # Decode image
            img_data = base64.b64decode(task['frame_data'])
            np_arr = np.frombuffer(img_data, dtype=np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            
            if frame is None: return
            
            # Run inference
            t_start = time.time()
            
            # Dual AI Interleaving Logic
            active_model = self.model
            if self.model_2 and (self.frames_processed % 2 != 0):
                active_model = self.model_2
            
            results = active_model(frame, verbose=False, conf=0.4)
            inference_time = (time.time() - t_start) * 1000
            
            detections = []
            for r in results:
                for box in r.boxes:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    conf = float(box.conf[0])
                    cls_id = int(box.cls[0])
                    cls_name = self.hazard_classes[cls_id] if cls_id < len(self.hazard_classes) else "Hazard"
                    
                    detections.append({
                        "class": cls_name,
                        "confidence": conf,
                        "bbox": [x1, y1, x2, y2],
                        "class_id": cls_id
                    })
            
            # Send results back
            res = {
                "type": "inference_result",
                "worker_id": self.worker_id,
                "frame_id": task.get('frame_id', 0),
                "detections": detections,
                "inference_ms": inference_time
            }
            self._send(res)
            
            self.frames_processed += 1
            self.detections_count += len(detections)
            
        except Exception as e:
            self.log(f"Inference error: {e}")

    def stop(self):
        self.running = False
        self.connected = False
        if self.socket:
            try: self.socket.close()
            except: pass

if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = WorkerGUI()
    app.mainloop()
