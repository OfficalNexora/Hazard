# Nexora Native - Settings View
# System configuration with sliders and toggles

import flet as ft
from core.config import COLORS
from core.bridge import bridge
from core.responsive import responsive_value


def create_settings_view(page: ft.Page) -> ft.Container:
    """Create settings view with threshold configuration"""
    
    padding = responsive_value(page, mobile=12, tablet=16, desktop=24)
    title_size = responsive_value(page, mobile=20, tablet=24, desktop=28)
    
    # Threshold sliders
    rain_slider = ft.Slider(min=0, max=100, value=40, divisions=20, label="{value}%")
    tilt_slider = ft.Slider(min=0, max=90, value=30, divisions=18, label="{value}°")
    confidence_slider = ft.Slider(min=0, max=100, value=70, divisions=20, label="{value}%")
    
    # Toggles
    audio_toggle = ft.Switch(value=True)
    led_toggle = ft.Switch(value=True)
    gsm_toggle = ft.Switch(value=True)
    
    # Save indicator
    save_status = ft.Text("", size=12, color=COLORS["emerald"])
    
    async def load_settings():
        settings = await bridge.fetch_settings()
        if settings:
            rain_slider.value = settings.get("rain_threshold", 40)
            tilt_slider.value = settings.get("tilt_threshold", 30)
            confidence_slider.value = settings.get("min_confidence", 70)
            audio_toggle.value = settings.get("audio_enabled", True)
            led_toggle.value = settings.get("led_enabled", True)
            gsm_toggle.value = settings.get("gsm_enabled", True)
            page.update()
    
    async def save_settings(e):
        save_status.value = "Saving..."
        page.update()
        
        success = await bridge.update_settings({
            "rain_threshold": rain_slider.value,
            "tilt_threshold": tilt_slider.value,
            "min_confidence": confidence_slider.value,
            "audio_enabled": audio_toggle.value,
            "led_enabled": led_toggle.value,
            "gsm_enabled": gsm_toggle.value,
        })
        
        save_status.value = "✓ Saved" if success else "✗ Failed"
        save_status.color = COLORS["emerald"] if success else COLORS["destructive"]
        page.update()
    
    page.run_task(load_settings)
    
    def create_setting_row(label: str, description: str, control) -> ft.Container:
        return ft.Container(
            padding=ft.padding.symmetric(vertical=12),
            content=ft.Row([
                ft.Column([
                    ft.Text(label, weight=ft.FontWeight.BOLD, color=COLORS["foreground"]),
                    ft.Text(description, size=12, color=COLORS["muted_foreground"]),
                ], spacing=2, expand=True),
                control,
            ]),
        )
    
    return ft.Container(
        expand=True,
        padding=padding,
        content=ft.Column([
            ft.Text("System Settings", size=title_size, weight=ft.FontWeight.BOLD, color=COLORS["foreground"]),
            ft.Text("Configure thresholds and system behavior", size=13, color=COLORS["muted_foreground"]),
            ft.Container(height=16),
            
            # Thresholds Card
            ft.Container(
                bgcolor=COLORS["card"],
                border_radius=12,
                border=ft.border.all(1, COLORS["border"]),
                padding=20,
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.icons.TUNE, color=COLORS["primary"]),
                        ft.Text("DETECTION THRESHOLDS", size=11, weight=ft.FontWeight.BOLD, color=COLORS["muted_foreground"]),
                    ], spacing=8),
                    ft.Divider(height=1, color=COLORS["border"]),
                    
                    ft.Text("Rain Alert Threshold", weight=ft.FontWeight.BOLD, color=COLORS["foreground"]),
                    ft.Text("Trigger alert when rain level exceeds this value", size=12, color=COLORS["muted_foreground"]),
                    rain_slider,
                    
                    ft.Text("Tilt Alert Threshold", weight=ft.FontWeight.BOLD, color=COLORS["foreground"]),
                    ft.Text("Trigger earthquake alert when tilt exceeds this angle", size=12, color=COLORS["muted_foreground"]),
                    tilt_slider,
                    
                    ft.Text("AI Confidence Threshold", weight=ft.FontWeight.BOLD, color=COLORS["foreground"]),
                    ft.Text("Minimum confidence for hazard detections", size=12, color=COLORS["muted_foreground"]),
                    confidence_slider,
                ], spacing=12),
            ),
            
            ft.Container(height=16),
            
            # Features Card
            ft.Container(
                bgcolor=COLORS["card"],
                border_radius=12,
                border=ft.border.all(1, COLORS["border"]),
                padding=20,
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.icons.SETTINGS, color=COLORS["primary"]),
                        ft.Text("SYSTEM FEATURES", size=11, weight=ft.FontWeight.BOLD, color=COLORS["muted_foreground"]),
                    ], spacing=8),
                    ft.Divider(height=1, color=COLORS["border"]),
                    
                    create_setting_row("Voice Announcements", "Enable TTS audio alerts", audio_toggle),
                    ft.Divider(height=1, color=COLORS["border"]),
                    create_setting_row("LED Guidance", "Enable LED strip evacuation guidance", led_toggle),
                    ft.Divider(height=1, color=COLORS["border"]),
                    create_setting_row("GSM Notifications", "Enable SMS/Call emergency alerts", gsm_toggle),
                ], spacing=0),
            ),
            
            ft.Container(height=24),
            
            # Save Button
            ft.Row([
                ft.ElevatedButton(
                    "Save Settings",
                    icon=ft.icons.SAVE,
                    bgcolor=COLORS["primary"],
                    color="white",
                    on_click=save_settings,
                ),
                save_status,
            ], spacing=16),
        ], scroll=ft.ScrollMode.AUTO),
    )
