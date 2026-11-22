"""مكونات واجهة المستخدم القابلة لإعادة الاستخدام لتطبيق Lader Tareiq."""
from __future__ import annotations

from typing import Optional

import flet as ft

from config import (
    COLOR_AMBER,
    COLOR_CARD,
    COLOR_CARD_BORDER,
    COLOR_CYAN,
    COLOR_GREEN,
    COLOR_MUTED,
    COLOR_PINK,
    COLOR_TEXT,
    COLOR_VIOLET,
)


def status_palette(status: str) -> tuple[str, str]:
    s = (status or "inactive").lower()
    mapping = {
        "active": (COLOR_GREEN, "مفعّل ونشط"),
        "expired": (COLOR_AMBER, "منتهي الصلاحية"),
        "banned": (COLOR_PINK, "محظور"),
        "device_limit": (COLOR_AMBER, "مرتبط بجهاز آخر"),
        "maintenance": (COLOR_VIOLET, "وضع الصيانة"),
    }
    return mapping.get(s, (COLOR_MUTED, "غير مفعّل"))


def build_section_card(
    title: str,
    subtitle: str,
    content: ft.Control,
    *,
    accent_color: str = COLOR_CYAN,
    badge_text: Optional[str] = None,
) -> ft.Container:
    header_right: list[ft.Control] = []
    if badge_text:
        header_right.append(
            ft.Container(
                content=ft.Text(
                    badge_text,
                    size=11,
                    weight=ft.FontWeight.BOLD,
                    color=accent_color,
                ),
                padding=ft.padding.symmetric(horizontal=10, vertical=4),
                border_radius=99,
                bgcolor="#121B3A",
                border=ft.border.all(1, accent_color),
            )
        )

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Container(
                            width=4,
                            height=34,
                            border_radius=4,
                            bgcolor=accent_color,
                        ),
                        ft.Column(
                            controls=[
                                ft.Text(
                                    title,
                                    size=16,
                                    weight=ft.FontWeight.BOLD,
                                    color=COLOR_TEXT,
                                ),
                                ft.Text(
                                    subtitle,
                                    size=12,
                                    color=COLOR_MUTED,
                                ),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                        *header_right,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Divider(height=12, color="#19254A"),
                content,
            ],
            spacing=8,
        ),
        padding=16,
        border_radius=16,
        bgcolor=COLOR_CARD,
        border=ft.border.all(1, COLOR_CARD_BORDER),
    )


def build_metric_tile(label: str, value: str, color: str = COLOR_CYAN) -> ft.Container:
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(value, size=18, weight=ft.FontWeight.BOLD, color=color),
                ft.Text(label, size=11, color=COLOR_MUTED),
            ],
            spacing=2,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=10, vertical=10),
        border_radius=12,
        bgcolor="#080D1F",
        border=ft.border.all(1, "#182447"),
        expand=True,
    )
