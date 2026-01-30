# Nexora Native - Main Application Entry Point
# Cross-platform Flet app (Windows EXE + Android APK)

import flet as ft
import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import COLORS, DIMENSIONS, NAV_ITEMS
from core.state import state
from core.bridge import bridge
from core.responsive import is_mobile, responsive_value, get_screen_size, ScreenSize

from components.sidebar import create_sidebar
from components.header import create_header

from views.dashboard import create_dashboard
from views.cameras import create_cameras_view
from views.devices import create_devices_view
from views.settings import create_settings_view
from views.alerts import create_alerts_view
from views.diorama import create_diorama_view


async def main(page: ft.Page):
    """Main application entry point"""
    
    # === PAGE CONFIGURATION ===
    page.title = "Nexora Mission Control"
    page.bgcolor = COLORS["background"]
    page.padding = 0
    page.spacing = 0
    page.theme_mode = ft.ThemeMode.DARK
    page.window.min_width = 320
    page.window.min_height = 480
    
    # Set window size for desktop
    if not is_mobile(page):
        page.window.width = 1280
        page.window.height = 800
    
    # === NAVIGATION STATE ===
    current_route = "dashboard"
    content_area = ft.Container(expand=True)
    
    # === VIEW FACTORY ===
    views = {
        "dashboard": lambda: create_dashboard(page),
        "cameras": lambda: create_cameras_view(page),
        "diorama": lambda: create_diorama_view(page),
        "devices": lambda: create_devices_view(page),
        "alerts": lambda: create_alerts_view(page),
        "settings": lambda: create_settings_view(page),
    }
    
    def navigate(route: str):
        nonlocal current_route
        current_route = route
        if route in views:
            content_area.content = views[route]()
        page.update()
    
    # Initial view
    navigate("dashboard")
    
    # === BUILD LAYOUT ===
    def build_layout():
        screen = get_screen_size(page.width or 1280)
        
        if screen == ScreenSize.MOBILE:
            # Mobile: No sidebar, bottom navigation
            return ft.Column([
                create_header(page),
                content_area,
                create_bottom_nav(page, navigate, current_route),
            ], spacing=0, expand=True)
        else:
            # Tablet/Desktop: Sidebar + Content
            return ft.Row([
                create_sidebar(page, navigate),
                ft.Column([
                    create_header(page),
                    content_area,
                ], spacing=0, expand=True),
            ], spacing=0, expand=True)
    
    page.add(build_layout())
    
    # === HANDLE RESIZE ===
    def on_resize(e):
        page.controls.clear()
        page.add(build_layout())
        # Re-navigate to refresh current view
        navigate(current_route)
    
    page.on_resized = on_resize
    
    # === START BRIDGE ===
    await bridge.connect()


def create_bottom_nav(page: ft.Page, navigate, current_route: str) -> ft.Container:
    """Create bottom navigation bar for mobile"""
    
    nav_items = NAV_ITEMS[:5]  # Limit to 5 for mobile
    
    def create_nav_item(item):
        is_active = item["id"] == current_route
        return ft.Container(
            expand=True,
            alignment=ft.alignment.center,
            on_click=lambda e, r=item["id"]: navigate(r),
            content=ft.Column([
                ft.Icon(
                    item["icon"],
                    size=24,
                    color=COLORS["primary"] if is_active else COLORS["muted_foreground"],
                ),
                ft.Text(
                    item["label"].split()[0],  # First word only
                    size=9,
                    color=COLORS["primary"] if is_active else COLORS["muted_foreground"],
                ),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
        )
    
    return ft.Container(
        height=64,
        bgcolor=COLORS["sidebar_bg"],
        border=ft.border.only(top=ft.BorderSide(1, COLORS["border"])),
        padding=ft.padding.symmetric(vertical=8),
        content=ft.Row(
            [create_nav_item(item) for item in nav_items],
            alignment=ft.MainAxisAlignment.SPACE_AROUND,
        ),
    )


# === RUN APPLICATION ===
if __name__ == "__main__":
    ft.run(main)
