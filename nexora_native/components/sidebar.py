# Nexora Native - Sidebar Component
import flet as ft
from core.config import COLORS, DIMENSIONS, NAV_ITEMS
from core.state import state


def create_sidebar(page: ft.Page, on_navigate) -> ft.Container:
    """Create the navigation sidebar"""
    
    nav_buttons = []
    current_route = "dashboard"
    
    def on_nav_click(e, route):
        nonlocal current_route
        current_route = route
        update_nav_state()
        on_navigate(route)
    
    def update_nav_state():
        for btn, item in zip(nav_buttons, NAV_ITEMS):
            if item["id"] == current_route:
                btn.bgcolor = COLORS["primary"]
                btn.content.controls[1].color = COLORS["foreground"]
            else:
                btn.bgcolor = "transparent"
                btn.content.controls[1].color = COLORS["muted_foreground"]
        page.update()
    
    # Create nav buttons
    for item in NAV_ITEMS:
        btn = ft.Container(
            content=ft.Row([
                ft.Icon(item["icon"], size=20, color=COLORS["muted_foreground"]),
                ft.Text(item["label"], size=13, color=COLORS["muted_foreground"]),
            ], spacing=12),
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            border_radius=8,
            bgcolor="transparent" if item["id"] != "dashboard" else COLORS["primary"],
            on_click=lambda e, r=item["id"]: on_nav_click(e, r),
            ink=True,
        )
        nav_buttons.append(btn)
    
    # Status indicator
    status_dot = ft.Container(
        width=8, height=8,
        bgcolor=COLORS["muted_foreground"],
        border_radius=4,
    )
    status_text = ft.Text("CONNECTING...", size=10, weight=ft.FontWeight.BOLD, color=COLORS["muted_foreground"])
    
    def on_connection(connected):
        if connected:
            status_dot.bgcolor = COLORS["emerald"]
            status_text.value = "SYSTEM ONLINE"
            status_text.color = COLORS["emerald"]
        else:
            status_dot.bgcolor = COLORS["muted_foreground"]
            status_text.value = "OFFLINE"
            status_text.color = COLORS["muted_foreground"]
        page.update()
    
    state.subscribe("connection", on_connection)
    
    return ft.Container(
        width=DIMENSIONS["sidebar_width"],
        bgcolor=COLORS["sidebar_bg"],
        border=ft.border.only(right=ft.BorderSide(1, COLORS["sidebar_border"])),
        content=ft.Column([
            # Branding
            ft.Container(
                padding=ft.padding.only(left=20, top=24, bottom=8),
                content=ft.Column([
                    ft.Text("NEXORA", size=28, weight=ft.FontWeight.BOLD, color=COLORS["foreground"]),
                    ft.Text("OPS COMMAND", size=10, color=COLORS["muted_foreground"], font_family="Consolas"),
                ], spacing=2),
            ),
            # Status
            ft.Container(
                padding=ft.padding.only(left=20, top=16, bottom=24),
                content=ft.Row([status_dot, status_text], spacing=8),
            ),
            # Navigation
            ft.Container(
                padding=ft.padding.symmetric(horizontal=12),
                content=ft.Column(nav_buttons, spacing=4),
            ),
            # Spacer
            ft.Container(expand=True),
            # Footer
            ft.Container(
                padding=ft.padding.only(left=20, bottom=20),
                content=ft.Text("v2.4.0-Native", size=9, color=COLORS["muted_foreground"], font_family="Consolas"),
            ),
        ]),
    )
