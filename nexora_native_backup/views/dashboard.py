# Nexora Native - Dashboard View
# Main Mission Control page (mirrors page.tsx)

import flet as ft
from datetime import datetime
from core.config import COLORS, HAZARD_COLORS, ALERT_STATES
from core.state import state
from core.bridge import bridge
from components.cards import create_stat_card, create_detection_card, create_override_button


def create_dashboard(page: ft.Page) -> ft.Container:
    """Create the main dashboard view"""
    
    # === STATS CARDS (dynamic) ===
    rain_value = ft.Text("0%", size=28, weight=ft.FontWeight.BOLD, color=COLORS["foreground"], font_family="Consolas")
    rain_bar = ft.ProgressBar(value=0, bgcolor=COLORS["muted"], color=COLORS["cyan"], height=6, border_radius=3)
    
    fire_value = ft.Text("CLEAR", size=28, weight=ft.FontWeight.BOLD, color=COLORS["emerald"], font_family="Consolas")
    fire_container = ft.Container(
        bgcolor=COLORS["card"],
        border_radius=12,
        border=ft.border.all(1, COLORS["border"]),
        padding=16,
        content=ft.Column([
            ft.Row([
                ft.Icon("local_fire_department", size=20, color=COLORS["destructive"]),
                ft.Text("FIRE MONITOR", size=10, weight=ft.FontWeight.BOLD, color=COLORS["muted_foreground"]),
            ], spacing=8),
            fire_value,
        ], spacing=8),
    )
    
    quake_x = ft.Text("0.0°", size=14, font_family="Consolas", color=COLORS["foreground"])
    quake_y = ft.Text("0.0°", size=14, font_family="Consolas", color=COLORS["foreground"])
    
    portal_code = ft.Text("------", size=28, weight=ft.FontWeight.BOLD, color=COLORS["primary"], font_family="Consolas")
    
    # === ACCELEROMETER (Intelligence Overview) ===
    accel_x = ft.Text("0.00", font_family="Consolas", color=COLORS["foreground"])
    accel_y = ft.Text("0.00", font_family="Consolas", color=COLORS["foreground"])
    accel_z = ft.Text("0.00", font_family="Consolas", color=COLORS["foreground"])
    
    # === DETECTION LOG ===
    detection_list = ft.Column([], spacing=8, scroll=ft.ScrollMode.AUTO)
    
    # === STATE SUBSCRIPTIONS ===
    def on_sensor(sensor):
        # Rain
        rain_value.value = f"{sensor.raining:.0f}%"
        rain_bar.value = sensor.raining / 100
        
        # Fire
        if sensor.fire:
            fire_value.value = "DETECTED"
            fire_value.color = COLORS["destructive"]
            fire_container.border = ft.border.all(2, COLORS["destructive"])
        else:
            fire_value.value = "CLEAR"
            fire_value.color = COLORS["emerald"]
            fire_container.border = ft.border.all(1, COLORS["border"])
        
        # Earthquake
        quake_x.value = f"{sensor.earthquake.get('x', 0):.1f}°"
        quake_y.value = f"{sensor.earthquake.get('y', 0):.1f}°"
        
        # Accelerometer
        accel_x.value = f"{sensor.accel.get('x', 0):.2f}"
        accel_y.value = f"{sensor.accel.get('y', 0):.2f}"
        accel_z.value = f"{sensor.accel.get('z', 0):.2f}"
        
        page.update()
    
    def on_detections(detections):
        detection_list.controls.clear()
        for det in detections[:10]:
            color = HAZARD_COLORS.get(det.class_name.lower(), HAZARD_COLORS["default"])
            ts = datetime.fromtimestamp(det.timestamp).strftime("%H:%M:%S") if det.timestamp else "NOW"
            detection_list.controls.append(
                create_detection_card(det.class_name, det.confidence, ts, color)
            )
        page.update()
    
    state.subscribe("sensor", on_sensor)
    state.subscribe("detections", on_detections)
    
    # Update portal code
    def update_code():
        portal_code.value = state.access_code
        page.update()
    state.subscribe("access_code", lambda _: update_code())
    
    # === OVERRIDE BUTTONS ===
    async def on_evacuate(e):
        await bridge.trigger_evacuation()
    
    async def on_safe(e):
        await bridge.set_safe_mode()
    
    async def on_fire_trigger(e):
        await bridge.trigger_manual("fire")
    
    async def on_rain_trigger(e):
        await bridge.trigger_manual("rain")
    
    # === LAYOUT ===
    stats_row = ft.Row([
        # Raining Monitor
        ft.Container(
            expand=True,
            bgcolor=COLORS["card"],
            border_radius=12,
            border=ft.border.all(1, COLORS["border"]),
            padding=16,
            content=ft.Column([
                ft.Row([
                    ft.Icon("water_drop", size=20, color=COLORS["cyan"]),
                    ft.Text("RAINING MONITOR", size=10, weight=ft.FontWeight.BOLD, color=COLORS["muted_foreground"]),
                ], spacing=8),
                rain_value,
                rain_bar,
            ], spacing=8),
        ),
        # Fire Monitor
        fire_container,
        # Earthquake Monitor
        ft.Container(
            expand=True,
            bgcolor=COLORS["card"],
            border_radius=12,
            border=ft.border.all(1, COLORS["border"]),
            padding=16,
            content=ft.Column([
                ft.Row([
                    ft.Icon("vibration", size=20, color=COLORS["amber"]),
                    ft.Text("EARTHQUAKE MONITOR", size=10, weight=ft.FontWeight.BOLD, color=COLORS["muted_foreground"]),
                ], spacing=8),
                ft.Row([
                    ft.Column([ft.Text("X-AXIS", size=9, color=COLORS["muted_foreground"]), quake_x]),
                    ft.Column([ft.Text("Y-AXIS", size=9, color=COLORS["muted_foreground"]), quake_y]),
                ], spacing=24),
            ], spacing=8),
        ),
        # Station Portal
        ft.Container(
            expand=True,
            bgcolor=COLORS["card"],
            border_radius=12,
            border=ft.border.all(1, COLORS["primary"] + "40"),
            padding=16,
            content=ft.Column([
                ft.Row([
                    ft.Icon("link", size=20, color=COLORS["primary"]),
                    ft.Text("STATION PORTAL", size=10, weight=ft.FontWeight.BOLD, color=COLORS["muted_foreground"]),
                ], spacing=8),
                portal_code,
                ft.Text("Public Access Code", size=11, color=COLORS["muted_foreground"]),
            ], spacing=8),
        ),
    ], spacing=16)
    
    # Intelligence Overview (left column)
    overview_card = ft.Container(
        expand=4,
        bgcolor=COLORS["card"],
        border_radius=12,
        border=ft.border.all(1, COLORS["border"]),
        padding=16,
        content=ft.Column([
            ft.Text("STATION INTELLIGENCE OVERVIEW", size=10, weight=ft.FontWeight.BOLD, color=COLORS["muted_foreground"]),
            ft.Divider(height=1, color=COLORS["border"]),
            # Accelerometer
            ft.Text("ACCELEROMETER READINGS", size=9, weight=ft.FontWeight.BOLD, color=COLORS["muted_foreground"]),
            ft.Row([
                ft.Column([ft.Text("X", size=9, color=COLORS["muted_foreground"]), accel_x]),
                ft.Column([ft.Text("Y", size=9, color=COLORS["muted_foreground"]), accel_y]),
                ft.Column([ft.Text("Z", size=9, color=COLORS["muted_foreground"]), accel_z]),
            ], spacing=32),
            ft.Divider(height=1, color=COLORS["border"]),
            # Override Buttons
            ft.Text("EMERGENCY OVERRIDES", size=9, weight=ft.FontWeight.BOLD, color=COLORS["muted_foreground"]),
            ft.Row([
                create_override_button("EVACUATE", "emergency", COLORS["destructive"], on_evacuate),
                create_override_button("SAFE MODE", "check_circle", COLORS["emerald"], on_safe),
            ], spacing=8),
            ft.Row([
                create_override_button("FIRE TRIGGER", "local_fire_department", COLORS["amber"], on_fire_trigger),
                create_override_button("RAIN TRIGGER", "water_drop", COLORS["cyan"], on_rain_trigger),
            ], spacing=8),
        ], spacing=12),
    )
    
    # Intelligence Log (right column)
    log_card = ft.Container(
        expand=3,
        bgcolor=COLORS["card"],
        border_radius=12,
        border=ft.border.all(1, COLORS["border"]),
        padding=16,
        content=ft.Column([
            ft.Row([
                ft.Icon("psychology", size=20, color=COLORS["violet"]),
                ft.Text("INTELLIGENCE LOG", size=10, weight=ft.FontWeight.BOLD, color=COLORS["muted_foreground"]),
            ], spacing=8),
            ft.Divider(height=1, color=COLORS["border"]),
            ft.Container(
                expand=True,
                content=detection_list,
            ),
        ], spacing=8),
    )
    
    main_row = ft.Row([overview_card, log_card], spacing=16, expand=True)
    
    return ft.Container(
        expand=True,
        padding=24,
        content=ft.Column([
            ft.Text("Mission Control", size=28, weight=ft.FontWeight.BOLD, color=COLORS["foreground"]),
            ft.Text("Real-time hazard monitoring and emergency response", size=13, color=COLORS["muted_foreground"]),
            ft.Container(height=16),
            stats_row,
            ft.Container(height=16),
            main_row,
        ]),
    )
