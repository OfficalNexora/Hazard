# Nexora Native - Alerts History View
# Historical alert log (mirrors alerts/page.tsx)

import flet as ft
from datetime import datetime
from core.config import COLORS, ALERT_STATES
from core.bridge import bridge
from core.responsive import responsive_value


def create_alerts_view(page: ft.Page) -> ft.Container:
    """Create alerts history view"""
    
    padding = responsive_value(page, mobile=12, tablet=16, desktop=24)
    title_size = responsive_value(page, mobile=20, tablet=24, desktop=28)
    
    alert_list = ft.Column([], scroll=ft.ScrollMode.AUTO, spacing=8, expand=True)
    
    async def load_history():
        history = await bridge.fetch_history()
        if history:
            alert_list.controls.clear()
            for event in history.get("events", [])[:50]:
                alert_list.controls.append(create_alert_row(event))
            page.update()
    
    page.run_task(load_history)
    
    return ft.Container(
        expand=True,
        padding=padding,
        content=ft.Column([
            ft.Row([
                ft.Column([
                    ft.Text("Alert History", size=title_size, weight=ft.FontWeight.BOLD, color=COLORS["foreground"]),
                    ft.Text("Historical log of all system alerts", size=13, color=COLORS["muted_foreground"]),
                ]),
                ft.Container(expand=True),
                ft.ElevatedButton("Refresh", icon=ft.icons.REFRESH, on_click=lambda e: page.run_task(load_history)),
            ]),
            ft.Container(height=16),
            ft.Container(
                expand=True,
                bgcolor=COLORS["card"],
                border_radius=12,
                border=ft.border.all(1, COLORS["border"]),
                padding=16,
                content=alert_list,
            ),
        ]),
    )


def create_alert_row(event: dict) -> ft.Container:
    event_type = event.get("type", "unknown")
    timestamp = event.get("timestamp", 0)
    details = event.get("details", {})
    
    # Get color based on type
    color = COLORS["muted_foreground"]
    icon = ft.icons.INFO
    if "fire" in event_type.lower():
        color = COLORS["destructive"]
        icon = ft.icons.LOCAL_FIRE_DEPARTMENT
    elif "rain" in event_type.lower() or "flood" in event_type.lower():
        color = COLORS["cyan"]
        icon = ft.icons.WATER_DROP
    elif "earthquake" in event_type.lower() or "seismic" in event_type.lower():
        color = COLORS["amber"]
        icon = ft.icons.VIBRATION
    elif "evacuate" in event_type.lower():
        color = COLORS["rose"]
        icon = ft.icons.EMERGENCY
    
    # Format timestamp
    try:
        ts_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
    except:
        ts_str = "Unknown"
    
    return ft.Container(
        bgcolor=COLORS["muted"],
        border_radius=8,
        padding=12,
        border=ft.border.only(left=ft.BorderSide(3, color)),
        content=ft.Row([
            ft.Icon(icon, color=color, size=24),
            ft.Column([
                ft.Text(event_type.replace("_", " ").upper(), weight=ft.FontWeight.BOLD, color=COLORS["foreground"]),
                ft.Text(ts_str, size=11, color=COLORS["muted_foreground"], font_family="Consolas"),
            ], spacing=2, expand=True),
            ft.Text(
                details.get("confidence", details.get("value", "")),
                size=12,
                color=color,
                font_family="Consolas",
            ),
        ], spacing=12),
    )
