# Nexora Native - Cameras View
# Camera feeds grid with responsive layout

import flet as ft
from core.config import COLORS
from core.state import state
from core.responsive import is_mobile, responsive_value


def create_cameras_view(page: ft.Page) -> ft.Container:
    """Create the cameras grid view with responsive layout"""
    
    def get_columns():
        return responsive_value(page, mobile=1, tablet=2, desktop=2)
    
    camera_grid = ft.GridView(
        expand=True,
        runs_count=get_columns(),
        max_extent=600,
        child_aspect_ratio=16/9,
        spacing=responsive_value(page, mobile=8, tablet=12, desktop=16),
        run_spacing=responsive_value(page, mobile=8, tablet=12, desktop=16),
    )
    
    no_cameras = ft.Container(
        expand=True,
        alignment=ft.alignment.center,
        content=ft.Column([
            ft.Container(
                width=80, height=80,
                bgcolor=COLORS["muted"],
                border_radius=40,
                alignment=ft.alignment.center,
                content=ft.Icon("videocam_off", size=32, color=COLORS["muted_foreground"]),
            ),
            ft.Text("No Cameras Found", size=18, weight=ft.FontWeight.BOLD, color=COLORS["foreground"]),
            ft.Text("No active camera streams detected.", size=13, color=COLORS["muted_foreground"], text_align=ft.TextAlign.CENTER),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=12),
    )
    
    def update_cameras(devices):
        cameras = [d for d in devices if 'cam' in d.device_id.lower() or d.device_type == 'esp32_cam']
        
        if not cameras:
            camera_grid.visible = False
            no_cameras.visible = True
        else:
            camera_grid.visible = True
            no_cameras.visible = False
            camera_grid.controls.clear()
            
            for cam in cameras:
                camera_grid.controls.append(
                    create_camera_tile(page, cam.device_id, cam.connected)
                )
        page.update()
    
    state.subscribe("devices", update_cameras)
    
    padding = responsive_value(page, mobile=12, tablet=16, desktop=24)
    title_size = responsive_value(page, mobile=20, tablet=24, desktop=28)
    
    return ft.Container(
        expand=True,
        padding=padding,
        content=ft.Column([
            ft.Text("Surveillance Feeds", size=title_size, weight=ft.FontWeight.BOLD, color=COLORS["foreground"]),
            ft.Text("Real-time CCTV monitoring", size=13, color=COLORS["muted_foreground"]),
            ft.Container(height=16),
            ft.Stack([camera_grid, no_cameras], expand=True),
        ]),
    )


def create_camera_tile(page: ft.Page, device_id: str, connected: bool) -> ft.Container:
    """Create a single camera feed tile"""
    
    status_badge = ft.Container(
        bgcolor=COLORS["emerald"] if connected else COLORS["muted_foreground"],
        border_radius=4,
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
        content=ft.Text("LIVE" if connected else "OFFLINE", size=10, weight=ft.FontWeight.BOLD, color="white"),
    )
    
    video_placeholder = ft.Container(
        expand=True,
        bgcolor=COLORS["muted"],
        alignment=ft.alignment.center,
        content=ft.Icon("videocam", size=48, color=COLORS["muted_foreground"]),
    )
    
    return ft.Container(
        bgcolor=COLORS["card"],
        border_radius=12,
        border=ft.border.all(1, COLORS["border"]),
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=ft.Stack([
            video_placeholder,
            ft.Container(padding=12, alignment=ft.alignment.top_left, content=status_badge),
            ft.Container(
                padding=12,
                alignment=ft.alignment.bottom_left,
                gradient=ft.LinearGradient(
                    begin=ft.alignment.bottom_center,
                    end=ft.alignment.top_center,
                    colors=["#000000CC", "#00000000"],
                ),
                content=ft.Text(device_id.replace("_", " ").upper(), size=12, weight=ft.FontWeight.BOLD, color="white"),
            ),
        ]),
    )
