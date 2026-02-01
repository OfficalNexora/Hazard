import customtkinter as ctk
import os
import sys
import threading
import time
from PIL import Image, ImageTk
import cv2
import tkinter as tk # Added tkinter import

# Add core to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from core.bridge import CoreBridge
from core.map_view import DioramaCanvas
from core.vision import VisionStreamer

class NexoraNativeApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("NEXORA | NATIVE MISSION CONTROL")
        self.geometry("1280x800")
        ctk.set_appearance_mode("Dark")
        
        # Initialize Logic
        self.bridge = CoreBridge()
        self.bridge.start()
        
        # Vision Management
        self.streamers = {} # cam_id -> VisionStreamer
        self.active_stream = None
        
        # State
        self.current_view = "dashboard"
        
        self._setup_ui()
        self._update_loop()

    def _render_settings(self):
        self._clear_content()
        self.header = self._create_header("System Configuration & Tactical Comms")
        
        settings_frame = ctk.CTkScrollableFrame(self.content_area, fg_color="transparent")
        settings_frame.grid(row=1, column=0, padx=30, pady=20, sticky="nsew")
        settings_frame.grid_columnconfigure(0, weight=1)

        # 1. GSM Contacts Section
        contact_card = ctk.CTkFrame(settings_frame, corner_radius=12, border_width=1, border_color="#27272a")
        contact_card.pack(fill="x", pady=10)
        ctk.CTkLabel(contact_card, text="EMERGENCY CONTACT PROTOCOLS", font=ctk.CTkFont(size=12, weight="bold"), text_color="#3b82f6").pack(pady=10)
        
        self.num_entry = ctk.CTkEntry(contact_card, placeholder_text="Phone Number (+63...)", width=300)
        self.num_entry.pack(pady=5)
        
        ctk.CTkButton(contact_card, text="LINK PROTOCOL (Add Contact)", fg_color="#3b82f6", 
                      command=self._add_contact).pack(pady=10)

        # 2. Thresholds Section
        thresh_card = ctk.CTkFrame(settings_frame, corner_radius=12, border_width=1, border_color="#27272a")
        thresh_card.pack(fill="x", pady=10)
        ctk.CTkLabel(thresh_card, text="HAZARD DETECTION THRESHOLDS", font=ctk.CTkFont(size=12, weight="bold"), text_color="#ef4444").pack(pady=10)
        
        ctk.CTkLabel(thresh_card, text="Fire Sensitivity").pack()
        ctk.CTkSlider(thresh_card, from_=0, to=100).pack(pady=5)
        
        ctk.CTkLabel(thresh_card, text="Flood Alert Level (mm)").pack()
        ctk.CTkSlider(thresh_card, from_=0, to=50).pack(pady=5)

    def _add_contact(self):
        val = self.num_entry.get()
        if val:
            print(f"[Settings] Adding contact: {val}")
            self.num_entry.delete(0, 'end')
            # In a real app, this would call self.bridge or a backend API

    def _setup_ui(self):
        # Grid Configuration
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 1. Sidebar
        self.sidebar = ctk.CTkFrame(self, width=240, corner_radius=0, fg_color="#09090b")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(10, weight=1)

        self.logo = ctk.CTkLabel(self.sidebar, text="NEXORA", font=ctk.CTkFont(size=28, weight="bold", family="Orbitron"))
        self.logo.grid(row=0, column=0, padx=20, pady=30)

        # Navigation Buttons
        self.nav_btns = {}
        nav_items = [
            ("Dashboard", "dashboard"),
            ("Live Vision", "vision"),
            ("Intelligence", "intel"),
            ("Event Logs", "logs"),
            ("Settings", "settings")
        ]
        
        for i, (text, view) in enumerate(nav_items):
            btn = ctk.CTkButton(
                self.sidebar, text=text, height=45, corner_radius=8,
                fg_color="transparent" if view != self.current_view else "#3b82f6",
                text_color="white",
                font=ctk.CTkFont(size=14, weight="bold"),
                anchor="w",
                command=lambda v=view: self._switch_view(v)
            )
            btn.grid(row=i+1, column=0, padx=20, pady=5, sticky="ew")
            self.nav_btns[view] = btn

        # Status Footer
        self.status_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.status_frame.grid(row=11, column=0, padx=20, pady=20, sticky="ew")
        self.status_dot = ctk.CTkLabel(self.status_frame, text="●", text_color="#10b981", font=ctk.CTkFont(size=14))
        self.status_dot.pack(side="left")
        self.status_text = ctk.CTkLabel(self.status_frame, text="CORE ACTIVE", font=ctk.CTkFont(size=12))
        self.status_text.pack(side="left", padx=10)

        # 2. Main Content Area
        self.content_area = ctk.CTkFrame(self, corner_radius=15, fg_color="#18181b") # Zinc-900
        self.content_area.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.content_area.grid_columnconfigure(0, weight=1)
        self.content_area.grid_rowconfigure(1, weight=1)

        self._render_dashboard()

    def _render_dashboard(self):
        # Clear current content
        for widget in self.content_area.winfo_children():
            widget.destroy()

        # Header
        self.header = ctk.CTkLabel(
            self.content_area, text="Mission Overview", 
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="#f4f4f5"
        )
        self.header.grid(row=0, column=0, padx=30, pady=(30, 10), sticky="w")

        # Metrics Row
        self.metrics_grid = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.metrics_grid.grid(row=1, column=0, padx=30, pady=10, sticky="nsew")
        self.metrics_grid.grid_columnconfigure((0,1,2,3), weight=1)

        self.fire_metric = self._create_metric_card(self.metrics_grid, "FIRE HAZARD", "SAFE", "#10b981", 0)
        self.rain_metric = self._create_metric_card(self.metrics_grid, "PRECIPITATION", "0.0mm", "#3b82f6", 1)
        self.seismic_metric = self._create_metric_card(self.metrics_grid, "SEISMIC ACTIVITY", "STABLE", "#8b5cf6", 2)
        
        # System Health Card (Small Terminal)
        self.health_card = ctk.CTkFrame(self.metrics_grid, height=120, corner_radius=12, fg_color="#0a0a0a", border_width=1, border_color="#27272a")
        self.health_card.grid(row=0, column=3, padx=10, sticky="nsew")
        ctk.CTkLabel(self.health_card, text="SYSTEM HEALTH", font=ctk.CTkFont(size=9, weight="bold"), text_color="#10b981").pack(pady=(10,0))
        self.health_logs = ctk.CTkLabel(self.health_card, text="CPU: 12%\nMEM: 242MB\nZMQ: OK", font=ctk.CTkFont(family="Consolas", size=10), text_color="#10b981")
        self.health_logs.pack(pady=5)

        # Center Workspace (Floorplan Placeholder)
        self.map_frame = ctk.CTkFrame(self.content_area, corner_radius=15, fg_color="#09090b")
        self.map_frame.grid(row=2, column=0, padx=30, pady=20, sticky="nsew")
        self.content_area.grid_rowconfigure(2, weight=3)
        
        self.map_label = ctk.CTkLabel(self.map_frame, text="3D MISSION MAP\n[ NATIVE RENDERER ]", 
                                     font=ctk.CTkFont(size=14, weight="bold"), text_color="#3f3f46")
        self.map_label.pack(expand=True)

    def _create_metric_card(self, parent, label, value, color, col):
        card = ctk.CTkFrame(parent, height=120, corner_radius=12, border_width=1, border_color="#27272a")
        card.grid(row=0, column=col, padx=10, sticky="nsew")
        
        lbl = ctk.CTkLabel(card, text=label, font=ctk.CTkFont(size=11, weight="bold"), text_color="#a1a1aa")
        lbl.pack(pady=(20, 0))
        
        val = ctk.CTkLabel(card, text=value, font=ctk.CTkFont(size=24, weight="bold"), text_color=color)
        val.pack(pady=(5, 20))
        return val

    def _switch_view(self, view):
        self.current_view = view
        for v, btn in self.nav_btns.items():
            btn.configure(fg_color="#3b82f6" if v == view else "transparent")
        
        if view == "dashboard":
            self._render_dashboard()
        elif view == "vision":
            self._render_vision()
        elif view == "intel":
            self._render_intel()
        elif view == "logs":
            self._render_map()
        elif view == "settings":
            self._render_settings()
        else:
            # Placeholder for other views
            for widget in self.content_area.winfo_children():
                widget.destroy()
            ctk.CTkLabel(self.content_area, text=f"{view.upper()} VIEW UNDER CONSTRUCTION", 
                         font=ctk.CTkFont(size=20)).pack(expand=True)

    def _render_vision(self):
        self._clear_content()
        self.header = self._create_header("Internal Surveillance Grid")
        
        # Camera Grid (2x2)
        grid_frame = ctk.CTkFrame(self.content_area, fg_color="transparent")
        grid_frame.grid(row=1, column=0, padx=30, pady=20, sticky="nsew")
        grid_frame.grid_columnconfigure((0, 1), weight=1)
        grid_frame.grid_rowconfigure((0, 1), weight=1)

        self.cams = []
        for i in range(4):
            cam_box = ctk.CTkFrame(grid_frame, corner_radius=12, border_width=1, border_color="#27272a")
            cam_box.grid(row=i//2, column=i%2, padx=10, pady=10, sticky="nsew")
            
            lbl = ctk.CTkLabel(cam_box, text=f"TACTICAL FEED-{i+1:02d}", font=ctk.CTkFont(family="Consolas", size=10, weight="bold"))
            lbl.pack(pady=5)
            
            display = ctk.CTkLabel(cam_box, text="[ LINKING TO NEURAL HUB... ]", text_color="#3f3f46", font=("Consolas", 10))
            display.pack(expand=True, fill="both", padx=2, pady=2)
            self.cams.append(display)
            
            # Start streaming if we have a valid endpoint (mocking for now, would be ESP32 IPs)
            # In a real setup, we'd fetch these from the model/bridge
            self._start_stream(i, display)

    def _start_stream(self, cam_id, display_label):
        """Initialize a native stream for a specific camera."""
        # Use existing server as proxy or direct ESP32 IP
        url = f"http://localhost:8000/api/camera/{cam_id}/stream" 
        
        def update_frame(rgb_frame):
            try:
                img = Image.fromarray(rgb_frame)
                # Fit to label
                w = display_label.winfo_width()
                h = display_label.winfo_height()
                if w > 10 and h > 10:
                    img = img.resize((w, h), Image.Resampling.LANCZOS)
                
                img_tk = ImageTk.PhotoImage(image=img)
                display_label.configure(image=img_tk, text="")
                display_label.image = img_tk
            except: pass

        streamer = VisionStreamer(url, update_frame)
        streamer.start()
        self.streamers[cam_id] = streamer

    def _render_intel(self):
        self._clear_content()
        self.header = self._create_header("Tactical Intelligence Feed")
        
        # Intelligence List
        self.intel_frame = ctk.CTkFrame(self.content_area, corner_radius=15, fg_color="#09090b")
        self.intel_frame.grid(row=1, column=0, padx=30, pady=20, sticky="nsew")
        
        self.intel_list = ctk.CTkTextbox(self.intel_frame, 
                                        fg_color="transparent", 
                                        font=ctk.CTkFont(family="Consolas", size=13),
                                        text_color="#10b981")
        self.intel_list.pack(fill="both", expand=True, padx=20, pady=20)
        self.intel_list.insert("0.0", ">>> INITIALIZING TACTICAL NEURAL LINK...\n>>> CONNECTION ESTABLISHED\n>>> MONITORING ACTIVE ZONES\n" + "-"*40 + "\n")

    def _clear_content(self):
        for widget in self.content_area.winfo_children():
            widget.destroy()

    def _render_map(self):
        self._clear_content()
        self.header = self._create_header("Tactical Digital Twin (Digital Command)")
        
        # Map Container
        self.map_container = ctk.CTkFrame(self.content_area, corner_radius=15, fg_color="#09090b")
        self.map_container.grid(row=1, column=0, padx=30, pady=20, sticky="nsew")
        
        # Integrated Native Map
        self.map_view = DioramaCanvas(self.map_container, bg="#09090b")
        self.map_view.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.map_view.refresh()

    def _draw_floorplan(self):
        pass # Replaced by DioramaCanvas logic

    def _update_loop(self):
        """Update UI with live data from the bridge."""
        sys_state = self.bridge.get_system_state()
        if sys_state and self.current_view == "dashboard":
            # Update metric cards
            fire = sys_state.get("fire", False)
            rain = sys_state.get("raining", 0.0)
            
            self.fire_metric.configure(text="DANGER" if fire else "SAFE", 
                                        text_color="#ef4444" if fire else "#10b981")
            self.rain_metric.configure(text=f"{rain:.1f}mm")
            self.seismic_metric.configure(text="STABLE") # Mock for now
            
            # Update map if active
            if self.current_view == "logs":
                # Calculate paths based on current hazards
                hazard_zones = []
                if fire: 
                    # Simulating hazard identification (Zone 1 is usually first floor)
                    hazard_zones = [1, 4]
                
                paths = {}
                if self.map_view.pathfinder:
                    paths = self.map_view.pathfinder.find_all_evacuation_routes(hazard_zones)
                
                self.map_view.refresh(hazard_zones=hazard_zones, paths=paths)

        # Update Intelligence Feed if active
        if self.current_view == "intel":
            detections = self.bridge.detections
            if detections:
                self.intel_list.delete("0.0", "end")
                for d in reversed(detections):
                    ts = time.strftime("[%H:%M:%S]")
                    label = d.get("class", "Unknown")
                    conf = d.get("confidence", 0.0)
                    self.intel_list.insert("end", f"{ts} ALERT: {label} detected (Confidence: {conf:.0%})\n")

        self.after(500, self._update_loop)

if __name__ == "__main__":
    app = NexoraNativeApp()
    app.mainloop()
