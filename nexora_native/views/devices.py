# Nexora Native - Devices View
# Device management (GSM contacts, Cluster workers)

import flet as ft
from core.config import COLORS
from core.state import state
from core.bridge import bridge
from core.responsive import responsive_value


def create_devices_view(page: ft.Page) -> ft.Container:
    """Create devices management view with tabs"""
    
    padding = responsive_value(page, mobile=12, tablet=16, desktop=24)
    title_size = responsive_value(page, mobile=20, tablet=24, desktop=28)
    
    # === SMS CONTACTS TAB ===
    sms_list = ft.Column([], scroll=ft.ScrollMode.AUTO, spacing=8)
    
    # === CALL CONTACTS TAB ===
    call_list = ft.Column([], scroll=ft.ScrollMode.AUTO, spacing=8)
    
    # === CLUSTER WORKERS TAB ===
    worker_list = ft.Column([], scroll=ft.ScrollMode.AUTO, spacing=8)
    
    async def load_contacts():
        contacts = await bridge.fetch_gsm_contacts()
        sms_list.controls.clear()
        call_list.controls.clear()
        
        for c in contacts.get("sms", []):
            sms_list.controls.append(create_contact_row(c, "sms"))
        for c in contacts.get("call", []):
            call_list.controls.append(create_contact_row(c, "call"))
        page.update()
    
    def on_devices(devices):
        worker_list.controls.clear()
        workers = [d for d in devices if d.device_type == "worker"]
        for w in workers:
            worker_list.controls.append(create_worker_row(w))
        page.update()
    
    state.subscribe("devices", on_devices)
    page.run_task(load_contacts)
    
    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=200,
        tabs=[
            ft.Tab(
                text="SMS Contacts",
                icon=ft.icons.SMS,
                content=ft.Container(
                    padding=16,
                    content=ft.Column([
                        ft.Row([
                            ft.Text("Emergency SMS Recipients", weight=ft.FontWeight.BOLD, color=COLORS["foreground"]),
                            ft.Container(expand=True),
                            ft.ElevatedButton("Add Contact", icon=ft.icons.ADD, on_click=lambda e: show_add_dialog(page, "sms")),
                        ]),
                        ft.Divider(height=1, color=COLORS["border"]),
                        ft.Container(expand=True, content=sms_list),
                    ]),
                ),
            ),
            ft.Tab(
                text="Call Contacts",
                icon=ft.icons.PHONE,
                content=ft.Container(
                    padding=16,
                    content=ft.Column([
                        ft.Row([
                            ft.Text("Emergency Call Recipients", weight=ft.FontWeight.BOLD, color=COLORS["foreground"]),
                            ft.Container(expand=True),
                            ft.ElevatedButton("Add Contact", icon=ft.icons.ADD, on_click=lambda e: show_add_dialog(page, "call")),
                        ]),
                        ft.Divider(height=1, color=COLORS["border"]),
                        ft.Container(expand=True, content=call_list),
                    ]),
                ),
            ),
            ft.Tab(
                text="Cluster Workers",
                icon=ft.icons.COMPUTER,
                content=ft.Container(
                    padding=16,
                    content=ft.Column([
                        ft.Row([
                            ft.Text("Connected Workers", weight=ft.FontWeight.BOLD, color=COLORS["foreground"]),
                            ft.Container(expand=True),
                            ft.Text("Auto-discovered via UDP", size=11, color=COLORS["muted_foreground"]),
                        ]),
                        ft.Divider(height=1, color=COLORS["border"]),
                        ft.Container(expand=True, content=worker_list),
                    ]),
                ),
            ),
        ],
        expand=True,
    )
    
    return ft.Container(
        expand=True,
        padding=padding,
        content=ft.Column([
            ft.Text("Device Management", size=title_size, weight=ft.FontWeight.BOLD, color=COLORS["foreground"]),
            ft.Text("Manage GSM contacts and cluster workers", size=13, color=COLORS["muted_foreground"]),
            ft.Container(height=16),
            ft.Container(
                expand=True,
                bgcolor=COLORS["card"],
                border_radius=12,
                border=ft.border.all(1, COLORS["border"]),
                content=tabs,
            ),
        ]),
    )


def create_contact_row(contact: dict, mode: str) -> ft.Container:
    return ft.Container(
        bgcolor=COLORS["muted"],
        border_radius=8,
        padding=12,
        content=ft.Row([
            ft.Icon(ft.icons.SMS if mode == "sms" else ft.icons.PHONE, color=COLORS["primary"]),
            ft.Column([
                ft.Text(contact.get("name", "Unknown"), weight=ft.FontWeight.BOLD, color=COLORS["foreground"]),
                ft.Text(contact.get("number", ""), size=12, color=COLORS["muted_foreground"], font_family="Consolas"),
            ], spacing=2),
            ft.Container(expand=True),
            ft.IconButton(icon=ft.icons.DELETE, icon_color=COLORS["destructive"], icon_size=20),
        ], spacing=12),
    )


def create_worker_row(worker) -> ft.Container:
    return ft.Container(
        bgcolor=COLORS["muted"],
        border_radius=8,
        padding=12,
        content=ft.Row([
            ft.Container(
                width=8, height=8,
                bgcolor=COLORS["emerald"] if worker.connected else COLORS["muted_foreground"],
                border_radius=4,
            ),
            ft.Column([
                ft.Text(worker.device_id, weight=ft.FontWeight.BOLD, color=COLORS["foreground"]),
                ft.Text(worker.device_type, size=12, color=COLORS["muted_foreground"]),
            ], spacing=2),
            ft.Container(expand=True),
            ft.Text("GPU Computing", size=11, color=COLORS["primary"]),
        ], spacing=12),
    )


def show_add_dialog(page: ft.Page, mode: str):
    name_field = ft.TextField(label="Name", border_color=COLORS["border"])
    number_field = ft.TextField(label="Phone Number", border_color=COLORS["border"])
    
    async def on_save(e):
        await bridge.add_gsm_contact(mode, number_field.value, name_field.value)
        page.close(dialog)
    
    dialog = ft.AlertDialog(
        title=ft.Text(f"Add {mode.upper()} Contact"),
        content=ft.Column([name_field, number_field], tight=True, spacing=16),
        actions=[
            ft.TextButton("Cancel", on_click=lambda e: page.close(dialog)),
            ft.ElevatedButton("Save", on_click=on_save),
        ],
    )
    page.open(dialog)
