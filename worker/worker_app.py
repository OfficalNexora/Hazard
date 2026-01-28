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
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# =============================================================================
# MODERN GUI APPLICATION
# =============================================================================
class WorkerGUI(ctk.CTk):
    """
    I designed this GUI to provide a premium, mission-critical interface for our AI cluster.
    It now supports dual roles: acting as the primary Command Center (Main) or a Specialist AI Node (Sub).
    """
    def __init__(self):
        super().__init__()

        self.title("NEXORA OPS | Distributed AI Node")
        self.geometry("1000x750")
        
        # Application State
        self.worker = None
        self.is_connected = False
        
        # UI State Variables
        self.role_var = tk.StringVar(value="SUB-WORKER (SPECIALIST)")
        self.specialty_var = tk.StringVar(value="Generalist")
        self.name_var = tk.StringVar(value=f"Node-{socket.gethostname()}")
        self.ip_var = tk.StringVar(value="auto")
        self.model_var = tk.StringVar(value="yolov8n.pt")
        
        self._setup_ui()
        self._load_config()
        
    def _setup_ui(self):
        # 1. Main Layout Grid
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 2. Side Navigation (Glassmorphism look)
        self.sidebar = ctk.CTkFrame(self, width=240, corner_radius=0, fg_color="#0f172a") # Deep Slate
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(6, weight=1)

        logo_label = ctk.CTkLabel(self.sidebar, text="NEXORA", font=ctk.CTkFont(size=24, weight="bold", family="Orbitron"))
        logo_label.grid(row=0, column=0, padx=20, pady=(30, 5))
        
        tagline = ctk.CTkLabel(self.sidebar, text="HAZARD DETECTION CLUSTER", font=ctk.CTkFont(size=10, family="Consolas"), text_color="#64748b")
        tagline.grid(row=1, column=0, padx=20, pady=(0, 30))

        # ROLE SELECTOR
        ctk.CTkLabel(self.sidebar, text="SYSTEM ROLE", font=ctk.CTkFont(size=10, weight="bold"), text_color="#3b82f6").grid(row=2, column=0, padx=20, pady=(10, 5), sticky="w")
        self.role_menu = ctk.CTkOptionMenu(self.sidebar, values=["COMMAND CENTER (MAIN)", "SUB-WORKER (SPECIALIST)"],
                                         variable=self.role_var, command=self._on_role_change,
                                         fg_color="#1e293b", button_color="#334155", button_hover_color="#475569")
        self.role_menu.grid(row=3, column=0, padx=20, pady=(0, 20))

        # STATUS INDICATOR
        self.status_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.status_frame.grid(row=4, column=0, padx=20, pady=10)
        self.status_dot = ctk.CTkLabel(self.status_frame, text="●", text_color="#ef4444", font=ctk.CTkFont(size=18))
        self.status_dot.pack(side="left", padx=5)
        self.status_text = ctk.CTkLabel(self.status_frame, text="OFFLINE", font=ctk.CTkFont(weight="bold", size=13))
        self.status_text.pack(side="left")

        # MAIN START BUTTON
        self.start_btn = ctk.CTkButton(self.sidebar, text="INITIALIZE NODE", height=45, font=ctk.CTkFont(weight="bold"),
                                       command=self.toggle_worker, fg_color="#3b82f6", hover_color="#2563eb")
        self.start_btn.grid(row=5, column=0, padx=20, pady=20)

        # 3. Main Workspace
        self.workspace = ctk.CTkFrame(self, fg_color="transparent")
        self.workspace.grid(row=0, column=1, padx=30, pady=30, sticky="nsew")
        self.workspace.grid_columnconfigure(0, weight=1)
        self.workspace.grid_rowconfigure(2, weight=1)

        # HEADER SECTION
        self.header = ctk.CTkFrame(self.workspace, fg_color="transparent")
        self.header.grid(row=0, column=0, sticky="ew", pady=(0, 25))
        
        self.title_label = ctk.CTkLabel(self.header, text="UNINITIALIZED NODE", font=ctk.CTkFont(size=28, weight="bold"))
        self.title_label.pack(side="left")

        # CONFIGURATION CARDS (Grid)
        self.config_grid = ctk.CTkFrame(self.workspace, fg_color="transparent")
        self.config_grid.grid(row=1, column=0, sticky="ew")
        self.config_grid.grid_columnconfigure((0, 1), weight=1)

        self.id_card = ctk.CTkFrame(self.config_grid, border_width=1, border_color="#1e293b")
        self.id_card.grid(row=0, column=0, padx=(0, 10), sticky="nsew")
        
        ctk.CTkLabel(self.id_card, text="CORE IDENTITY", font=ctk.CTkFont(size=11, weight="bold"), text_color="#10b981").pack(pady=(15, 5))
        ctk.CTkEntry(self.id_card, textvariable=self.name_var, height=35).pack(fill="x", padx=20, pady=5)
        
        ctk.CTkLabel(self.id_card, text="INFERENCE SPECIALTY", font=ctk.CTkFont(size=11, weight="bold"), text_color="#f59e0b").pack(pady=(15, 5))
        self.specialty_menu = ctk.CTkOptionMenu(self.id_card, values=["Generalist", "Fire Specialist", "Smoke Specialist", "Flood Detector", "Custom Models"],
                                               variable=self.specialty_var, height=35,
                                               fg_color="#1e293b", button_color="#334155")
        self.specialty_menu.pack(fill="x", padx=20, pady=(0, 20))

        # CARD: Network & Engine
        self.net_card = ctk.CTkFrame(self.config_grid, border_width=1, border_color="#1e293b")
        self.net_card.grid(row=0, column=1, padx=(10, 0), sticky="nsew")
        
        ctk.CTkLabel(self.net_card, text="NETWORK ENDPOINT", font=ctk.CTkFont(size=11, weight="bold"), text_color="#06b6d4").pack(pady=(15, 5))
        ctk.CTkEntry(self.net_card, textvariable=self.ip_var, placeholder_text="auto-discover").pack(fill="x", padx=20, pady=5)
        
        ctk.CTkLabel(self.net_card, text="PRIMARY AI MODEL", font=ctk.CTkFont(size=11, weight="bold"), text_color="#8b5cf6").pack(pady=(15, 5))
        self.model_menu = ctk.CTkOptionMenu(self.net_card, values=["yolov8n.pt", "yolov8s.pt", "custom_hazard.pt"],
                                           variable=self.model_var, height=35,
                                           fg_color="#1e293b", button_color="#334155")
        self.model_menu.pack(fill="x", padx=20, pady=(0, 20))

        # STATS ROW (Glass cards)
        self.stats_row = ctk.CTkFrame(self.workspace, fg_color="transparent")
        self.stats_row.grid(row=2, column=0, sticky="ew", pady=25)
        self.stats_row.grid_columnconfigure((0, 1, 2), weight=1)

        self.fps_stat = self._create_stat_card(self.stats_row, 0, "INFERENCE FPS", "0.0", "#ef4444")
        self.det_stat = self._create_stat_card(self.stats_row, 1, "TOTAL DETECTIONS", "0", "#10b981")
        self.lat_stat = self._create_stat_card(self.stats_row, 2, "LATENCY (MS)", "0", "#3b82f6")

        # LOGS SECTION
        self.log_container = ctk.CTkFrame(self.workspace, border_width=1, border_color="#1e293b")
        self.log_container.grid(row=3, column=0, sticky="nsew")
        self.log_container.grid_rowconfigure(1, weight=1)
        self.log_container.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(self.log_container, text="CLUSTERING SYSTEM LOGS", font=ctk.CTkFont(size=11, weight="bold"), text_color="#64748b").grid(row=0, column=0, padx=20, pady=10, sticky="w")
        self.log_area = ctk.CTkTextbox(self.log_container, font=("Consolas", 11), text_color="#10b981", fg_color="#0a0a0a")
        self.log_area.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")

    def _create_stat_card(self, parent, col, title, value, accent_color):
        card = ctk.CTkFrame(parent, border_width=1, border_color="#1e293b")
        card.grid(row=0, column=col, padx=5, sticky="nsew")
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=10, weight="bold"), text_color="#64748b").pack(pady=(10, 0))
        label = ctk.CTkLabel(card, text=value, font=ctk.CTkFont(size=32, weight="bold"), text_color=accent_color)
        label.pack(pady=(0, 10))
        return label

    def _on_role_change(self, choice):
        if choice == "COMMAND CENTER (MAIN)":
            self.title_label.configure(text="COMMAND CENTER SYSTEM", text_color="#3b82f6")
            self.specialty_menu.configure(state="disabled")
            self.ip_var.set("LOCAL (MASTER)")
            self.log("SWITCHED TO MAIN STATION MODE. Ready to coordinate AI cluster.")
        else:
            self.title_label.configure(text="SPECIALIZED SUB-WORKER", text_color="#ffffff")
            self.specialty_menu.configure(state="normal")
            self.ip_var.set("auto")
            self.log("SWITCHED TO SUB-WORKER MODE. Searching for Main Command Center...")

    def log(self, message):
        ts = time.strftime("[%H:%M:%S]")
        self.after(0, lambda: self.log_area.insert("end", f"{ts} {message}\n"))
        self.after(0, lambda: self.log_area.see("end"))

    def _load_config(self):
        # Auto-detect Role
        self._on_role_change(self.role_var.get())
        if not YOLO_AVAILABLE:
            self.log("WARNING: ULTRALYTICS NOT FOUND. AI OFFLINE.")
        if not CV2_AVAILABLE:
            self.log("WARNING: OPENCV NOT FOUND. CAMERA OFFLINE.")

    def toggle_worker(self):
        if self.worker and self.worker.running:
            self.stop_worker()
        else:
            self.start_worker()

    def start_worker(self):
        if self.role_var.get() == "COMMAND CENTER (MAIN)":
            self.log("NEXORA CORE INITIALIZED. Connect workers via port 8001.")
            self.status_dot.configure(text_color="#10b981")
            self.status_text.configure(text="MASTER ACTIVE")
            self.start_btn.configure(text="SHUTDOWN BRAIN", fg_color="#ef4444")
            return

        name = self.name_var.get()
        model = self.model_var.get()
        specialty = self.specialty_var.get()
        server_ip = self.ip_var.get()
        
        self.worker = WorkerApp(self, name, model, server_ip if server_ip != 'auto' else None, specialty=specialty)
        self.worker_thread = threading.Thread(target=self.worker.start, daemon=True)
        self.worker_thread.start()
        
        self.start_btn.configure(text="TERMINATE NODE", fg_color="#ef4444")
        self.status_dot.configure(text_color="#f59e0b")
        self.status_text.configure(text="SYNCING...")

    def stop_worker(self):
        if self.worker:
            self.worker.stop()
        self.start_btn.configure(text="INITIALIZE NODE", fg_color="#3b82f6")
        self.status_dot.configure(text_color="#ef4444")
        self.status_text.configure(text="OFFLINE")
        self.log("NODAL CONNECTION SEVERED.")
        
    def update_status(self, connected):
        self.is_connected = connected
        if connected:
            self.status_dot.configure(text_color="#10b981")
            self.status_text.configure(text="LINKED")
        else:
            self.status_dot.configure(text_color="#f59e0b")
            self.status_text.configure(text="RETRYING...")

    def update_stats(self, fps, detections, latency):
        self.fps_stat.configure(text=f"{fps:.1f}")
        self.det_stat.configure(text=f"{detections}")
        self.lat_stat.configure(text=f"{latency:.0f}")

    def change_appearance_mode(self, new_mode):
        ctk.set_appearance_mode(new_mode)

# =============================================================================
# WORKER CORE LOGIC
# =============================================================================
class WorkerApp:
    def __init__(self, gui, name, model_path, server_ip=None, specialty="Generalist"):
        self.gui = gui
        self.name = name
        self.model_path = model_path
        self.specialty = specialty
        self.server_ip = server_ip
        
        self.worker_id = f"{name}_{int(time.time())}"
        self.running = False
        self.connected = False
        self.socket = None
        self.model = None
        
        self.frames_processed = 0
        self.detections_count = 0
        self.start_time = time.time()
        
        self.class_names = [
            "Fire", "Smoke", "Flood", "Falling Debris",
            "Landslide", "Explosion", "Collapsed Structure", "Industrial Accident"
        ]

    def log(self, msg):
        self.gui.log(msg)

    def start(self):
        self.running = True
        
        if YOLO_AVAILABLE:
            try:
                self.log(f"Loading Specialized Engine: {self.model_path}")
                self.model = YOLO(self.model_path)
            except Exception as e:
                self.log(f"Engine failure: {e}")
                self.running = False
                return

        if not self.server_ip:
            self.log("Scanning Cluster Frequency (UDP 8002)...")
            self.server_ip = self._discover()
        
        if self.server_ip:
            self._connect()
        else:
            self.log("Handshake Error: Main Command Center not broadcasting.")
            self.running = False
            self.gui.after(0, self.gui.stop_worker)
            return

        if self.connected:
            self._main_loop()

    def _discover(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(5)
        try:
            sock.bind(('', DEFAULT_DISCOVERY_PORT))
            data, addr = sock.recvfrom(1024)
            msg = json.loads(data.decode("utf-8", errors="replace"))
            if msg.get('type') == 'server_announce':
                ip = msg.get('ip') or addr[0]
                self.log(f"Frequency Lock: Brain detected at {ip}")
                return ip
        except Exception as e:
            self.log(f"Discovery timeout: {e}")
        finally:
            sock.close()
        return None

    def _connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server_ip, DEFAULT_SERVER_PORT))
            
            # Capability Handshake
            reg = {
                "type": "register",
                "worker_id": self.worker_id,
                "name": self.name,
                "model": self.model_path,
                "specialty": self.specialty,
                "role": "sub-worker"
            }
            self._send(reg)
            self.connected = True
            self.gui.after(0, lambda: self.gui.update_status(True))
            self.log(f"Linked to Neural Hub: {self.server_ip}")
        except Exception as e:
            self.log(f"Handshake failed: {e}")
            self.connected = False

    def _send(self, msg):
        if not self.socket: return
        try:
            data = json.dumps(msg).encode()
            self.socket.sendall(struct.pack('>I', len(data)) + data)
        except:
            self.connected = False

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
            return json.loads(data.decode("utf-8", errors="replace"))
        except:
            return None

    def _main_loop(self):
        last_heartbeat = 0
        while self.running and self.connected:
            try:
                # Heartbeat
                if time.time() - last_heartbeat > HEARTBEAT_INTERVAL:
                    stats = {
                        "fps": self.frames_processed / (time.time() - self.start_time) if (time.time() - self.start_time) > 0 else 0,
                        "detections": self.detections_count,
                        "specialty": self.specialty
                    }
                    self._send({"type": "heartbeat", "worker_id": self.worker_id, "stats": stats})
                    last_heartbeat = time.time()
                    
                self.socket.settimeout(0.5)
                task = self._receive()
                if task and task.get('type') == 'inference_task':
                    self._do_inference(task)
                
                elapsed = time.time() - self.start_time
                fps = self.frames_processed / elapsed if elapsed > 0 else 0
                self.gui.after(0, lambda: self.gui.update_stats(fps, self.detections_count, 0))
                
            except socket.timeout:
                continue
            except Exception as e:
                self.log(f"HUB LINK SEVERED: {e}")
                self.connected = False
                self.gui.after(0, lambda: self.gui.update_status(False))
                break

    def _do_inference(self, task):
        if not self.model or not CV2_AVAILABLE: return
        try:
            img_data = base64.b64decode(task['frame_data'])
            np_arr = np.frombuffer(img_data, dtype=np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            
            if frame is None: return
            
            t_start = time.time()
            results = self.model(frame, verbose=False, conf=0.4)
            inference_time = (time.time() - t_start) * 1000
            
            detections = []
            for r in results:
                for box in r.boxes:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    conf = float(box.conf[0])
                    cls_id = int(box.cls[0])
                    cls_name = self.class_names[cls_id] if cls_id < len(self.class_names) else "Hazard"
                    
                    detections.append({
                        "class": cls_name,
                        "confidence": conf,
                        "bbox": [x1, y1, x2, y2],
                        "specialist": self.specialty
                    })
            
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
            self.log(f"AI FAULT: {e}")

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
