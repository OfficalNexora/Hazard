# Nexora Native - Header Component
import flet as ft
import asyncio
from datetime import datetime
from core.config import COLORS, DIMENSIONS


def create_header(page: ft.Page) -> ft.Container:
    """Create the top header bar"""
    
    time_text = ft.Text("00:00:00", size=14, weight=ft.FontWeight.BOLD, color=COLORS["primary"], font_family="Consolas")
    
    # Start time update task
    async def time_loop():
        while True:
            time_text.value = datetime.now().strftime("%H:%M:%S")
            try:
                page.update()
            except:
                pass
            await asyncio.sleep(1)
    
    page.run_task(time_loop)
    
    return ft.Container(
        height=DIMENSIONS["header_height"],
        bgcolor=COLORS["background"],
        border=ft.border.only(bottom=ft.BorderSide(1, COLORS["border"])),
        padding=ft.padding.symmetric(horizontal=24),
        content=ft.Row([
            # Search bar
            ft.Container(
                width=384,
                height=36,
                bgcolor=COLORS["muted"],
                border_radius=8,
                padding=ft.padding.only(left=12),
                content=ft.Row([
                    ft.Icon("search", size=16, color=COLORS["muted_foreground"]),
                    ft.Text("Search logs, devices, or alerts...", size=13, color=COLORS["muted_foreground"]),
                ], spacing=8),
            ),
            ft.Container(expand=True),
            # Secure badge
            ft.Container(
                bgcolor=COLORS["muted"],
                border_radius=20,
                padding=ft.padding.symmetric(horizontal=16, vertical=6),
                content=ft.Row([
                    ft.Icon("verified_user", size=16, color=COLORS["emerald"]),
                    ft.Text("SECURE", size=10, weight=ft.FontWeight.BOLD, color=COLORS["muted_foreground"]),
                ], spacing=6),
            ),
            # Clock
            time_text,
            # Notification bell
            ft.IconButton(
                icon="notifications",
                icon_color=COLORS["muted_foreground"],
                icon_size=20,
                on_click=lambda e: None,
            ),
        ], alignment=ft.MainAxisAlignment.START),
    )
