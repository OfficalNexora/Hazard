import tkinter as tk
import math
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../backend")))
try:
    from backend.diorama_model import get_model
    from backend.pathfinder import get_pathfinder
except ImportError:
    get_model = None
    get_pathfinder = None

class DioramaCanvas(tk.Canvas):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, highlightthickness=0, **kwargs)
        self.model = get_model() if get_model else None
        self.pathfinder = get_pathfinder() if get_pathfinder else None
        
        # View Settings (Isometric-ish)
        self.scale = 3000 # Scaling factor for meters to pixels
        self.offset_x = 400
        self.offset_y = 500
        self.angle = 45 # Rotation
        self.selected_cam = None
        
        self.bind("<Configure>", self.refresh)
        self.bind("<Button-1>", self._on_click)

    def _on_click(self, event):
        # Very simple hit detection for cameras
        for i, cam in enumerate(self.model.cameras):
            sx, sy = self.project(*cam.position)
            if abs(event.x - sx) < 15 and abs(event.y - sy) < 15:
                print(f"[MapView] Selected Camera {i}")
                self.selected_cam = i
                self.refresh()
                return

    def project(self, x, y, z):
        """Project 3D world coordinates to 2D screen coordinates."""
        # Simple isometric projection
        rad = math.radians(self.angle)
        px = (x - y) * math.cos(rad)
        py = (x + y) * math.sin(rad) - z
        
        return self.offset_x + px * self.scale, self.offset_y + py * self.scale

    def refresh(self, event=None, hazard_zones=None, paths=None):
        self.delete("all")
        if not self.model:
            self.create_text(200, 200, text="NO MODEL LOADED", fill="white")
            return

        # 1. Draw Buildings
        for b in self.model.buildings:
            self._draw_box(b.bounds, color="#1e293b", outline="#334155")

        # 2. Draw Zones
        for z in self.model.get_all_zones():
            color = "#0f172a"
            if hazard_zones and z.id in hazard_zones:
                color = "#7f1d1d" # Danger Red
            elif z.is_exit:
                color = "#064e3b" # Exit Green
            
            # Draw zone center point
            sx, sy = self.project(*z.position)
            self.create_oval(sx-5, sy-5, sx+5, sy+5, fill=color, outline="#94a3b8")
            self.create_text(sx, sy+15, text=z.name, fill="#94a3b8", font=("Inter", 8))

        # 3. Draw Paths
        if paths:
            for start_id, result in paths.items():
                if result.valid and len(result.path) > 1:
                    last_point = None
                    for zid in result.path:
                        zone = self.model.get_zone_by_id(zid)
                        if zone:
                            curr_point = self.project(*zone.position)
                            if last_point:
                                self.create_line(last_point[0], last_point[1], 
                                               curr_point[0], curr_point[1], 
                                               fill="#10b981", width=2, arrow="last", dash=(4,4))
                            last_point = curr_point

        # 4. Draw Cameras
        for i, cam in enumerate(self.model.cameras):
            sx, sy = self.project(*cam.position)
            color = "#f59e0b" if self.selected_cam == i else "#64748b"
            # Draw camera glyph
            self.create_oval(sx-8, sy-8, sx+8, sy+8, fill="#0f172a", outline=color, width=2)
            self.create_text(sx, sy, text="📷", fill=color, font=("Inter", 10))
            self.create_text(sx, sy-20, text=f"CAM-{i+1}", fill=color, font=("Inter", 8, "bold"))

    def _draw_box(self, bounds, color, outline):
        """Draw a 3D-perspective box for building bounds."""
        min_x, min_y, min_z, max_x, max_y, max_z = bounds
        
        # Corner projections
        p1 = self.project(min_x, min_y, min_z)
        p2 = self.project(max_x, min_y, min_z)
        p3 = self.project(max_x, max_y, min_z)
        p4 = self.project(min_x, max_y, min_z)
        
        p5 = self.project(min_x, min_y, max_z)
        p6 = self.project(max_x, min_y, max_z)
        p7 = self.project(max_x, max_y, max_z)
        p8 = self.project(min_x, max_y, max_z)
        
        # Draw Base
        self.create_polygon(p1, p2, p3, p4, fill=color, outline=outline, alpha=0.5)
        # Draw Top
        self.create_polygon(p5, p6, p7, p8, fill=color, outline=outline)
        # Vertical edges
        self.create_line(p1, p5, fill=outline)
        self.create_line(p2, p6, fill=outline)
        self.create_line(p3, p7, fill=outline)
        self.create_line(p4, p8, fill=outline)
