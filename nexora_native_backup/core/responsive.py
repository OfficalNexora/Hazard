# Nexora Native - Responsive Layout Utilities
# Transparent compatibility for Windows desktop and Android mobile

import flet as ft
from enum import Enum
from typing import Callable


class ScreenSize(Enum):
    MOBILE = "mobile"       # < 600px (phones)
    TABLET = "tablet"       # 600-1024px (tablets, small laptops)
    DESKTOP = "desktop"     # > 1024px (desktops)


def get_screen_size(width: float) -> ScreenSize:
    """Determine screen size category"""
    if width < 600:
        return ScreenSize.MOBILE
    elif width < 1024:
        return ScreenSize.TABLET
    return ScreenSize.DESKTOP


def is_mobile(page: ft.Page) -> bool:
    """Check if running on mobile-sized screen"""
    return page.width < 600 if page.width else False


def is_tablet(page: ft.Page) -> bool:
    """Check if running on tablet-sized screen"""
    return 600 <= page.width < 1024 if page.width else False


def is_desktop(page: ft.Page) -> bool:
    """Check if running on desktop-sized screen"""
    return page.width >= 1024 if page.width else True


def responsive_value(page: ft.Page, mobile, tablet=None, desktop=None):
    """Return value based on screen size"""
    if is_mobile(page):
        return mobile
    elif is_tablet(page):
        return tablet if tablet is not None else mobile
    else:
        return desktop if desktop is not None else (tablet if tablet is not None else mobile)


def responsive_columns(page: ft.Page) -> int:
    """Get grid columns based on screen size"""
    return responsive_value(page, mobile=1, tablet=2, desktop=4)


def responsive_padding(page: ft.Page) -> int:
    """Get padding based on screen size"""
    return responsive_value(page, mobile=12, tablet=16, desktop=24)


def responsive_sidebar_width(page: ft.Page) -> int:
    """Get sidebar width (hidden on mobile)"""
    return responsive_value(page, mobile=0, tablet=200, desktop=256)


def responsive_font_size(page: ft.Page, base: int) -> int:
    """Scale font size for screen"""
    return responsive_value(page, mobile=int(base * 0.85), tablet=base, desktop=base)


class ResponsiveRow(ft.ResponsiveRow):
    """Pre-configured responsive row"""
    def __init__(self, controls, **kwargs):
        super().__init__(
            controls=controls,
            spacing=16,
            run_spacing=16,
            **kwargs
        )


class ResponsiveContainer(ft.Container):
    """Container that adapts padding to screen size"""
    def __init__(self, page: ft.Page, content, **kwargs):
        padding = responsive_padding(page)
        super().__init__(
            content=content,
            padding=padding,
            **kwargs
        )


def create_adaptive_layout(page: ft.Page, sidebar, header, content) -> ft.Control:
    """
    Create layout that adapts to screen size:
    - Desktop: Sidebar + Header + Content
    - Tablet: Collapsible sidebar + Header + Content  
    - Mobile: Bottom nav + Content (no sidebar)
    """
    
    screen = get_screen_size(page.width or 1280)
    
    if screen == ScreenSize.MOBILE:
        # Mobile: Stack layout with bottom navigation
        return ft.Column([
            # Header (simplified)
            header,
            # Content (full width)
            ft.Container(expand=True, content=content),
            # Bottom navigation
            create_bottom_nav(page, sidebar),
        ], spacing=0, expand=True)
    
    elif screen == ScreenSize.TABLET:
        # Tablet: Thinner sidebar
        return ft.Row([
            ft.Container(width=200, content=sidebar),
            ft.Column([header, ft.Container(expand=True, content=content)], spacing=0, expand=True),
        ], spacing=0, expand=True)
    
    else:
        # Desktop: Full sidebar
        return ft.Row([
            sidebar,
            ft.Column([header, ft.Container(expand=True, content=content)], spacing=0, expand=True),
        ], spacing=0, expand=True)


def create_bottom_nav(page: ft.Page, sidebar_ref) -> ft.Container:
    """Create bottom navigation for mobile"""
    from core.config import COLORS, NAV_ITEMS
    
    nav_items = NAV_ITEMS[:5]  # Limit to 5 items for mobile
    
    return ft.Container(
        bgcolor=COLORS["sidebar_bg"],
        border=ft.border.only(top=ft.BorderSide(1, COLORS["border"])),
        padding=ft.padding.symmetric(vertical=8),
        content=ft.Row(
            [
                ft.IconButton(
                    icon=item["icon"],
                    icon_color=COLORS["muted_foreground"],
                    icon_size=24,
                    tooltip=item["label"],
                )
                for item in nav_items
            ],
            alignment=ft.MainAxisAlignment.SPACE_AROUND,
        ),
    )


def create_responsive_card_grid(page: ft.Page, cards: list) -> ft.Control:
    """Create responsive grid of cards"""
    cols = responsive_columns(page)
    
    if cols == 1:
        # Mobile: Vertical stack
        return ft.Column(cards, spacing=12)
    else:
        # Tablet/Desktop: Responsive row with wrapping
        return ft.ResponsiveRow(
            [
                ft.Container(
                    col={"xs": 12, "sm": 6, "md": 4, "lg": 3},
                    content=card,
                )
                for card in cards
            ],
            spacing=16,
            run_spacing=16,
        )
