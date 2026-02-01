# Nexora Native - Design Configuration (Flet Compatible)
# 1:1 Parity with globals.css OKLCH tokens

# =============================================================================
# COLOR PALETTE (OKLCH -> HEX)
# =============================================================================
COLORS = {
    # Core
    "background": "#0f1117",
    "foreground": "#fafafa",
    "card": "#1a1d24",
    "card_foreground": "#fafafa",
    
    # Borders
    "border": "#2a2d35",
    "muted": "#1f2229",
    "muted_foreground": "#9ca3af",
    
    # Primary
    "primary": "#3b82f6",
    "primary_foreground": "#ffffff",
    
    # Destructive
    "destructive": "#ef4444",
    "destructive_foreground": "#ffffff",
    
    # Status
    "emerald": "#10b981",
    "amber": "#f59e0b",
    "cyan": "#22d3ee",
    "rose": "#f43f5e",
    "violet": "#8b5cf6",
    
    # Sidebar
    "sidebar_bg": "#0a0c10",
    "sidebar_border": "#1e2028",
    
    # Alerts
    "alert_safe": "#10b981",
    "alert_calling": "#f59e0b",
    "alert_messaging": "#3b82f6",
    "alert_danger": "#ef4444",
    "alert_evacuate": "#f43f5e",
}

HAZARD_COLORS = {
    "fire": "#ef4444",
    "smoke": "#6b7280",
    "person": "#3b82f6",
    "flood": "#06b6d4",
    "debris": "#f59e0b",
    "default": "#8b5cf6",
}

# =============================================================================
# DIMENSIONS
# =============================================================================
DIMENSIONS = {
    "sidebar_width": 256,
    "header_height": 56,
    "card_padding": 16,
    "card_radius": 12,
    "button_height": 40,
}

# =============================================================================
# API CONFIG
# =============================================================================
API_CONFIG = {
    "base_url": "http://localhost:8000",
    "ws_url": "ws://localhost:8000/ws/telemetry",
}

# =============================================================================
# NAVIGATION
# =============================================================================
NAV_ITEMS = [
    {"id": "dashboard", "label": "Mission Control", "icon": "dashboard"},
    {"id": "cameras", "label": "Cameras", "icon": "videocam"},
    {"id": "diorama", "label": "Digital Twin", "icon": "view_in_ar"},
    {"id": "devices", "label": "Devices", "icon": "devices"},
    {"id": "alerts", "label": "Alert History", "icon": "notifications"},
    {"id": "settings", "label": "Settings", "icon": "settings"},
]

ALERT_STATES = {
    0: {"name": "SAFE", "color": COLORS["alert_safe"]},
    1: {"name": "CALLING", "color": COLORS["alert_calling"]},
    2: {"name": "MESSAGING", "color": COLORS["alert_messaging"]},
    3: {"name": "DANGER", "color": COLORS["alert_danger"]},
    4: {"name": "EVACUATE", "color": COLORS["alert_evacuate"]},
}
