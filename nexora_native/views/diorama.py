# Nexora Native - Digital Twin View
# 2D visualization using Flet controls (Flet doesn't have 3D canvas)

import flet as ft
import math
from core.config import COLORS, HAZARD_COLORS
from core.state import state
from core.bridge import bridge
from core.responsive import responsive_value


def create_diorama_view(page: ft.Page) -> ft.Container:
    """Create Digital Twin visualization using Flet containers"""
    
    padding = responsive_value(page, mobile=12, tablet=16, desktop=24)
    title_size = responsive_value(page, mobile=20, tablet=24, desktop=28)
    
    # Model data placeholder
    model_data = {"buildings": [], "zones": [], "exits": []}
    hazard_state = {"fire": False, "rain": False, "earthquake": False}
    
    # Buildings container
    buildings_stack = ft.Stack(expand=True)
    
    async def load_model():
        result = await bridge.fetch_diorama_model()
        if result:
            model_data["buildings"] = result.get("buildings", [])
            model_data["zones"] = result.get("zones", [])
            model_data["exits"] = result.get("exits", [])
        redraw()
    
    def on_sensor(sensor):
        hazard_state["fire"] = sensor.fire
        hazard_state["rain"] = sensor.raining > 40
        hazard_state["earthquake"] = abs(sensor.earthquake.get("x", 0)) > 15 or abs(sensor.earthquake.get("y", 0)) > 15
        redraw()
    
    state.subscribe("sensor", on_sensor)
    page.run_task(load_model)
    
    def redraw():
        buildings_stack.controls.clear()
        
        # Draw grid background
        grid = create_grid()
        buildings_stack.controls.append(grid)
        
        # Draw buildings
        for building in model_data.get("buildings", []):
            buildings_stack.controls.append(create_building_widget(building))
        
        # Draw zones
        for zone in model_data.get("zones", []):
            buildings_stack.controls.append(create_zone_widget(zone, hazard_state))
        
        # Draw exits
        for exit_point in model_data.get("exits", []):
            buildings_stack.controls.append(create_exit_widget(exit_point))
        
        # If no model loaded, show placeholder
        if not model_data.get("buildings") and not model_data.get("zones"):
            buildings_stack.controls.append(create_placeholder())
        
        page.update()
    
    # Initial draw
    redraw()
    
    # Legend
    legend = ft.Row([
        create_legend_item("Building", COLORS["primary"]),
        create_legend_item("Safe Zone", COLORS["emerald"]),
        create_legend_item("Hazard Zone", COLORS["destructive"]),
        create_legend_item("Exit", COLORS["amber"]),
    ], spacing=16, wrap=True)
    
    # Status indicators
    status_row = ft.Row([
        create_status_indicator("Fire", hazard_state.get("fire", False), COLORS["destructive"]),
        create_status_indicator("Rain", hazard_state.get("rain", False), COLORS["cyan"]),
        create_status_indicator("Seismic", hazard_state.get("earthquake", False), COLORS["amber"]),
    ], spacing=16)
    
    return ft.Container(
        expand=True,
        padding=padding,
        content=ft.Column([
            ft.Row([
                ft.Column([
                    ft.Text("Digital Twin", size=title_size, weight=ft.FontWeight.BOLD, color=COLORS["foreground"]),
                    ft.Text("Real-time facility visualization", size=13, color=COLORS["muted_foreground"]),
                ], spacing=4),
                ft.Container(expand=True),
                status_row,
            ]),
            ft.Container(height=8),
            legend,
            ft.Container(height=16),
            ft.Container(
                expand=True,
                bgcolor=COLORS["card"],
                border_radius=12,
                border=ft.border.all(1, COLORS["border"]),
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                content=buildings_stack,
            ),
        ]),
    )


def create_grid() -> ft.Container:
    """Create grid background"""
    return ft.Container(
        expand=True,
        bgcolor=COLORS["muted"],
    )


def create_building_widget(building: dict) -> ft.Container:
    """Create a building as a positioned container"""
    x = building.get("x", 0) * 60 + 50
    y = building.get("y", 0) * 60 + 50
    w = building.get("width", 2) * 50
    h = building.get("height", 2) * 50
    
    return ft.Container(
        left=x,
        top=y,
        width=w,
        height=h,
        bgcolor=COLORS["primary"] + "30",
        border=ft.border.all(2, COLORS["primary"]),
        border_radius=4,
        alignment=ft.alignment.center,
        content=ft.Text(
            building.get("name", "Building"),
            size=10,
            color=COLORS["foreground"],
            text_align=ft.TextAlign.CENTER,
        ),
    )


def create_zone_widget(zone: dict, hazard_state: dict) -> ft.Container:
    """Create a zone as a positioned circle"""
    x = zone.get("x", 0) * 60 + 50
    y = zone.get("y", 0) * 60 + 50
    r = zone.get("radius", 1) * 30
    
    zone_type = zone.get("type", "safe")
    
    # Determine color based on hazard state
    if zone_type == "fire" or hazard_state.get("fire"):
        color = COLORS["destructive"]
        opacity = 0.6
    elif hazard_state.get("rain"):
        color = COLORS["cyan"]
        opacity = 0.5
    elif hazard_state.get("earthquake"):
        color = COLORS["amber"]
        opacity = 0.5
    else:
        color = COLORS["emerald"]
        opacity = 0.4
    
    return ft.Container(
        left=x - r,
        top=y - r,
        width=r * 2,
        height=r * 2,
        bgcolor=color + hex(int(255 * opacity))[2:].zfill(2),
        border_radius=r,
        border=ft.border.all(1, color),
    )


def create_exit_widget(exit_point: dict) -> ft.Container:
    """Create an exit marker"""
    x = exit_point.get("x", 0) * 60 + 50
    y = exit_point.get("y", 0) * 60 + 50
    
    return ft.Container(
        left=x - 15,
        top=y - 15,
        width=30,
        height=30,
        bgcolor=COLORS["amber"],
        border_radius=4,
        alignment=ft.alignment.center,
        content=ft.Icon("exit_to_app", size=16, color="white"),
    )


def create_placeholder() -> ft.Container:
    """Create placeholder when no model loaded"""
    return ft.Container(
        expand=True,
        alignment=ft.alignment.center,
        content=ft.Column([
            ft.Container(
                width=80,
                height=80,
                bgcolor=COLORS["muted"],
                border_radius=40,
                alignment=ft.alignment.center,
                content=ft.Icon("view_in_ar", size=32, color=COLORS["muted_foreground"]),
            ),
            ft.Text("No Model Loaded", size=16, weight=ft.FontWeight.BOLD, color=COLORS["foreground"]),
            ft.Text("Start the backend to load the facility model", size=12, color=COLORS["muted_foreground"]),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=12),
    )


def create_legend_item(label: str, color: str) -> ft.Row:
    return ft.Row([
        ft.Container(width=12, height=12, bgcolor=color, border_radius=2),
        ft.Text(label, size=11, color=COLORS["muted_foreground"]),
    ], spacing=6)


def create_status_indicator(label: str, active: bool, color: str) -> ft.Container:
    return ft.Container(
        bgcolor=color if active else COLORS["muted"],
        border_radius=4,
        padding=ft.padding.symmetric(horizontal=12, vertical=6),
        content=ft.Row([
            ft.Container(
                width=8, height=8,
                bgcolor="white" if active else COLORS["muted_foreground"],
                border_radius=4,
            ),
            ft.Text(label, size=10, weight=ft.FontWeight.BOLD, color="white" if active else COLORS["muted_foreground"]),
        ], spacing=6),
    )
