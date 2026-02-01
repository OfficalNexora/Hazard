# Nexora Native - Stat Card Component
import flet as ft
from core.config import COLORS


def create_stat_card(
    title: str,
    value: str,
    icon: str,
    color: str = None,
    subtitle: str = None,
    progress: float = None,
) -> ft.Container:
    """Create a stats card (Raining, Fire, Earthquake, Portal)"""
    
    icon_color = color or COLORS["primary"]
    
    content_controls = [
        ft.Row([
            ft.Icon(icon, size=20, color=icon_color),
            ft.Text(title, size=10, weight=ft.FontWeight.BOLD, color=COLORS["muted_foreground"]),
        ], spacing=8),
        ft.Text(value, size=28, weight=ft.FontWeight.BOLD, color=COLORS["foreground"], font_family="Consolas"),
    ]
    
    if subtitle:
        content_controls.append(
            ft.Text(subtitle, size=11, color=COLORS["muted_foreground"])
        )
    
    if progress is not None:
        content_controls.append(
            ft.ProgressBar(
                value=progress / 100,
                bgcolor=COLORS["muted"],
                color=icon_color,
                height=6,
                border_radius=3,
            )
        )
    
    return ft.Container(
        bgcolor=COLORS["card"],
        border_radius=12,
        border=ft.border.all(1, COLORS["border"]),
        padding=16,
        content=ft.Column(content_controls, spacing=8),
    )


def create_detection_card(
    class_name: str,
    confidence: float,
    timestamp: str,
    color: str,
) -> ft.Container:
    """Create a detection log item"""
    
    return ft.Container(
        bgcolor=COLORS["card"],
        border_radius=8,
        border=ft.border.all(1, COLORS["border"]),
        padding=12,
        content=ft.Column([
            ft.Row([
                ft.Container(
                    width=8, height=8,
                    bgcolor=color,
                    border_radius=4,
                ),
                ft.Text(class_name.upper(), size=12, weight=ft.FontWeight.BOLD, color=COLORS["foreground"]),
                ft.Container(expand=True),
                ft.Text(f"{confidence:.0%}", size=11, color=COLORS["muted_foreground"], font_family="Consolas"),
            ], spacing=8),
            ft.ProgressBar(
                value=confidence,
                bgcolor=COLORS["muted"],
                color=color,
                height=4,
                border_radius=2,
            ),
            ft.Text(timestamp, size=9, color=COLORS["muted_foreground"]),
        ], spacing=6),
    )


def create_override_button(
    label: str,
    icon: str,
    color: str,
    on_click,
) -> ft.ElevatedButton:
    """Create an emergency override button"""
    
    return ft.ElevatedButton(
        content=ft.Row([
            ft.Icon(icon, size=16, color="white"),
            ft.Text(label, size=11, weight=ft.FontWeight.BOLD, color="white"),
        ], spacing=8, alignment=ft.MainAxisAlignment.CENTER),
        bgcolor=color,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
        ),
        on_click=on_click,
    )
