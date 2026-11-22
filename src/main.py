"""نقطة الدخول + الواجهة الفخمة لتطبيق Lader Tareiq: الرئيسية · الأدوات · السجل · الإعدادات.
Developed & Engineered by Lader Tareiq.
"""
from __future__ import annotations

import asyncio
import functools
import inspect
import re
import traceback
from datetime import datetime
from typing import Callable, Optional

import flet as ft

import api
import installer
import state
from config import CFG

# ---------------------------------------------------------------- الألوان والسمات
BG = "#05070E"
BG2 = "#0B1024"
PLATE = "#0C1124"
PLATE2 = "#131B38"
RULE = "#1E2A4F"
TEXT = "#EEF3FF"
MUT = "#8693BA"
CYAN = "#19E3FF"
VIOLET = "#8B5CFF"
PINK = "#FF2E93"
GREEN = "#38FFA2"
AMBER = "#FFB020"
DARK = "#031318"


def _safe(factory: Callable, default=None):
    try:
        return factory()
    except Exception:
        return default


def _icon(name: str, fallback=None):
    return getattr(ft.Icons, name, fallback or ft.Icons.INFO)


def _op(color: str, a: float) -> str:
    return _safe(lambda: ft.Colors.with_opacity(a, color), color)


def _glow(color: str, blur: int = 22, a: float = 0.45):
    sh = _safe(
        lambda: ft.BoxShadow(
            spread_radius=0,
            blur_radius=blur,
            color=_op(color, a),
            offset=ft.Offset(0, 0),
        )
    )
    return [sh] if sh is not None else None


def _grad(c1: str, c2: str, vertical: bool = False):
    return _safe(
        lambda: ft.LinearGradient(
            begin=ft.Alignment(0, -1) if vertical else ft.Alignment(-1, 0),
            end=ft.Alignment(0, 1) if vertical else ft.Alignment(1, 0),
            colors=[c1, c2],
        )
    )


def _vt(v: str) -> tuple:
    return tuple(int(x) for x in re.findall(r"\d+", v or "")[:4]) or (0,)


def _mb(n: float) -> str:
    return f"{n / 1048576:.1f}"


def guarded(fn):
    @functools.wraps(fn)
    async def wrapper(self, *a, **k):
        try:
            return await fn(self, *a, **k)
        except asyncio.CancelledError:
            raise
        except Exception as ex:
            try:
                self.set_busy(False)
                self.notify("err", "خطأ غير متوقع", str(ex))
            except Exception:
                pass

    return wrapper


class NButton:
    def __init__(
        self,
        text: str,
        icon=None,
        on_click=None,
        kind: str = "primary",
        visible: bool = True,
        height: int = 52,
    ):
        self._handler = on_click
        self.enabled = True
        self.kind = kind
        self.label = ft.Text(
            text,
            size=14.5,
            weight=ft.FontWeight.BOLD,
            text_align=ft.TextAlign.CENTER,
        )
        self.icon = ft.Icon(icon, size=20) if icon is not None else None
        row = ft.Row(
            [c for c in (self.icon, self.label) if c is not None],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=8,
        )
        self.control = ft.Container(
            content=row,
            height=height,
            border_radius=14,
            alignment=ft.Alignment.CENTER,
            on_click=self._click,
            ink=True,
            visible=visible,
        )
        self.apply_kind(kind)

    def apply_kind(self, kind: str) -> None:
        self.kind = kind
        c, lab = self.control, self.label
        c.gradient, c.bgcolor, c.border, c.shadow = None, None, None, None
        if kind == "primary":
            c.gradient = _grad(CYAN, VIOLET)
            c.bgcolor = None if c.gradient is not None else CYAN
            c.shadow = _glow(CYAN, 22, 0.38)
            fg = DARK
        elif kind == "danger":
            c.bgcolor = "#1B0B18"
            c.border = ft.Border.all(1, _op(PINK, 0.58))
            fg = PINK
        elif kind == "secondary":
            c.bgcolor = PLATE2
            c.border = ft.Border.all(1, _op(CYAN, 0.32))
            fg = TEXT
        else:
            c.bgcolor = _op(BG, 0.0)
            c.border = ft.Border.all(1, RULE)
            fg = MUT
        lab.color = fg
        if self.icon is not None:
            self.icon.color = fg

    def set_text(self, text: str) -> None:
        self.label.value = text

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        self.control.opacity = 1.0 if enabled else 0.45

    def set_url(self, url: str) -> None:
        self.control.url = url or None

    async def _click(self, e) -> None:
        if not self.enabled or self._handler is None:
            return
        res = self._handler(e)
        if inspect.isawaitable(res):
            await res


def card(content: ft.Control, accent: str = CYAN, **kw) -> ft.Container:
    return ft.Container(
        content=content,
        padding=18,
        border_radius=18,
        bgcolor=PLATE,
        border=ft.Border.all(1, _op(accent, 0.25)),
        shadow=_glow(accent, 28, 0.12),
        **kw,
    )


def title(text: str, size: int = 17, color: str = TEXT) -> ft.Text:
    return ft.Text(text, size=size, weight=ft.FontWeight.BOLD, color=color)


def kv_row(label: str, value: ft.Control) -> ft.Row:
    return ft.Row(
        [ft.Text(label, size=13.5, color=MUT), value],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )


def divider() -> ft.Container:
    return ft.Container(height=1, bgcolor=RULE, margin=2)


def chip(text: str, color: str) -> ft.Container:
    return ft.Container(
        content=ft.Text(text, size=11.5, weight=ft.FontWeight.BOLD, color=color),
        padding=ft.Padding.symmetric(horizontal=10, vertical=5),
        border_radius=99,
        border=ft.Border.all(1, _op(color, 0.7)),
        bgcolor=_op(color, 0.10),
    )


class App:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.busy = False
        self._clip = None
        self._armed: dict = {}
        self._last_pct = -1
        self._staged = None
        self._manual_kind = "install"
        self._diag: list = []
        self._banner_action = None
        self.tab = 0
        self.license: Optional[api.LicenseResult] = None
        st = state.load()
        self.installed_version: str = st.get("installed_version", "")
        self.deployed_name: str = st.get("deployed_name", "")
        self.auto_update: bool = bool(st.get("auto_update", False))
        self.notifications_enabled: bool = bool(st.get("notifications_enabled", True))
        self.ota_version: str = st.get("ota_version") or getattr(CFG, "OTA_VERSION", "1.0.0")
        self.ota_payload: dict = st.get("ota_payload") if isinstance(st.get("ota_payload"), dict) else {}
        self.support_url = ""
        self.device_id = api.get_device_id()

        # ===== الرأس الفخم لهوية Lader Tareiq =====
        self.status_chip = chip("غير مفعّل", MUT)
        self.dev_badge = chip(CFG.DEVELOPER_NAME, VIOLET)
        self.header = ft.Container(
            padding=ft.Padding.symmetric(horizontal=14, vertical=12),
            bgcolor=_op(PLATE, 0.75),
            border=ft.Border(bottom=ft.BorderSide(1, _op(CYAN, 0.16))),
            content=ft.Row(
                [
                    ft.Row(
                        [
                            ft.Container(
                                content=ft.Icon(_icon("VERIFIED_USER"), size=24, color=CYAN),
                                width=46,
                                height=46,
                                border_radius=14,
                                alignment=ft.Alignment.CENTER,
                                bgcolor=_op(CYAN, 0.12),
                                border=ft.Border.all(1, _op(CYAN, 0.45)),
                                shadow=_glow(CYAN, 18, 0.35),
                            ),
                            ft.Column(
                                [
                                    title(CFG.APP_TITLE, 17),
                                    ft.Text(
                                        f"v{CFG.APP_VERSION} • {CFG.DEVELOPER_TAGLINE}",
                                        size=11,
                                        color=MUT,
                                    ),
                                ],
                                spacing=2,
                            ),
                        ],
                        spacing=10,
                    ),
                    ft.Row([self.dev_badge, self.status_chip], spacing=6),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
        )

        # ===== بطاقات الحالة السريعة (Shizuku + التخزين + الباتش) =====
        self.shizuku_status_txt = ft.Text("جاري الفحص", size=12, weight=ft.FontWeight.BOLD, color=MUT)
        self.perm_status_txt = ft.Text("جاري الفحص", size=12, weight=ft.FontWeight.BOLD, color=MUT)
        self.patch_state_txt = ft.Text("غير مثبّت", size=12, weight=ft.FontWeight.BOLD, color=MUT)
        self.quick_bar = card(
            ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text("Shizuku", size=11, color=MUT),
                            self.shizuku_status_txt,
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    ft.Container(width=1, height=28, bgcolor=RULE),
                    ft.Column(
                        [
                            ft.Text("التخزين", size=11, color=MUT),
                            self.perm_status_txt,
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    ft.Container(width=1, height=28, bgcolor=RULE),
                    ft.Column(
                        [
                            ft.Text("الباتش", size=11, color=MUT),
                            self.patch_state_txt,
                        ],
                        spacing=2,
                        expand=True,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            accent=VIOLET,
        )

        # ===== الإشعارات الاحترافية والتنبيهات =====
        self.banner_icon = ft.Icon(_icon("CAMPAIGN"), size=20, color=CYAN)
        self.banner_text = ft.Text("", size=13, color=TEXT, expand=True)
        self.banner_btn = ft.TextButton("إجراء", on_click=self._on_banner_action, visible=False)
        self.banner_close = ft.IconButton(
            icon=_icon("CLOSE"),
            icon_size=16,
            icon_color=MUT,
            on_click=lambda _: self.hide_banner(),
        )
        self.banner = ft.Container(
            visible=False,
            padding=ft.Padding.symmetric(horizontal=14, vertical=10),
            border_radius=14,
            bgcolor=_op(CYAN, 0.09),
            border=ft.Border.all(1, _op(CYAN, 0.42)),
            content=ft.Row(
                [self.banner_icon, self.banner_text, self.banner_btn, self.banner_close],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )
        self.warn_text = ft.Text("", size=13.5, color=TEXT, expand=True)
        self.warn_banner = ft.Container(
            visible=False,
            padding=14,
            border_radius=14,
            bgcolor=_op(AMBER, 0.09),
            border=ft.Border.all(1, _op(AMBER, 0.55)),
            content=ft.Row(
                [ft.Icon(_icon("WARNING"), size=20, color=AMBER), self.warn_text],
                spacing=10,
            ),
        )

        # تحديث التطبيق الكبير (Full APK)
        self.update_msg = ft.Text("", size=14, color=TEXT, text_align=ft.TextAlign.CENTER)
        self.update_btn = NButton(
            "تحميل APK الجديد",
            _icon("SYSTEM_UPDATE"),
            visible=False,
        )
        self.update_panel = card(
            ft.Column(
                [
                    ft.Icon(_icon("SYSTEM_UPDATE"), size=44, color=CYAN),
                    title("تحديث APK مطلوب", 19),
                    self.update_msg,
                    self.update_btn.control,
                ],
                spacing=12,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            visible=False,
        )

        # التفعيل
        self.key_input = ft.TextField(
            label="كود التفعيل",
            password=True,
            can_reveal_password=True,
            text_align=ft.TextAlign.CENTER,
            on_submit=self.on_activate,
            border_radius=14,
            border_color=RULE,
            focused_border_color=CYAN,
            bgcolor=BG,
            color=TEXT,
        )
        self.activate_btn = NButton("تحقق وفعّل", _icon("SECURITY"), self.on_activate)
        self.perm_quick_btn = NButton(
            "فحص الأذونات وShizuku",
            _icon("ADMIN_PANEL_SETTINGS"),
            self.on_request_permissions,
            kind="secondary",
            height=46,
        )
        self.activation_card = card(
            ft.Column(
                [
                    ft.Row(
                        [
                            title("تفعيل اشتراك Lader Tareiq", 18),
                            chip("VIP", CYAN),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Text(
                        "أدخل كود التفعيل للتحقق الفوري وتجهيز الباتش أو المجلد تلقائياً.",
                        size=13,
                        color=MUT,
                    ),
                    ft.Container(height=2),
                    self.key_input,
                    self.activate_btn.control,
                    self.perm_quick_btn.control,
                ],
                spacing=12,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            )
        )

        # الحساب
        self.days_text = ft.Text("0", size=50, weight=ft.FontWeight.W_800, color=CYAN)
        self.days_label = ft.Text("يوم متبقٍ", size=14, color=MUT)
        self.meter = ft.ProgressBar(value=1, color=GREEN, bgcolor=RULE)
        self.expiry_text = ft.Text("", size=12.5, color=MUT)
        self.installed_text = ft.Text("غير مثبّت", size=14, weight=ft.FontWeight.W_600, color=TEXT)
        self.latest_text = ft.Text("—", size=14, weight=ft.FontWeight.W_600, color=TEXT)
        self.deployed_item_text = ft.Text("—", size=12.5, color=CYAN)
        self.update_badge = chip("تحديث متاح", AMBER)
        self.update_badge.visible = False
        self.notes_text = ft.Text("", size=13, color=TEXT)
        self.notes_box = ft.Container(
            visible=False,
            padding=12,
            border_radius=12,
            bgcolor=_op(VIOLET, 0.10),
            border=ft.Border.all(1, _op(VIOLET, 0.40)),
            content=ft.Column(
                [
                    ft.Text("ما الجديد", size=12, weight=ft.FontWeight.BOLD, color=VIOLET),
                    self.notes_text,
                ],
                spacing=4,
            ),
        )
        self.install_btn = NButton("تثبيت الباتش", _icon("DOWNLOAD"), self.on_install)
        self.remove_btn = NButton(
            "حذف الباتش",
            _icon("DELETE"),
            self.on_remove_click,
            kind="secondary",
        )
        self.account_card = card(
            ft.Column(
                [
                    ft.Row(
                        [title("اشتراكك", 17), chip("نشط", GREEN)],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Row(
                        [self.days_text, self.days_label],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.END,
                    ),
                    self.meter,
                    self.expiry_text,
                    divider(),
                    kv_row("الباتش المثبّت", ft.Row([self.update_badge, self.installed_text], spacing=8)),
                    kv_row("أحدث إصدار", self.latest_text),
                    kv_row("العنصر المنقول", self.deployed_item_text),
                    self.notes_box,
                    ft.Container(height=2),
                    self.install_btn.control,
                    self.remove_btn.control,
                ],
                spacing=10,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
            visible=False,
        )

        # حالة العملية
        self.status = ft.Text("", size=14, color=MUT, text_align=ft.TextAlign.CENTER)
        self.speed = ft.Text("", size=12, color=MUT, text_align=ft.TextAlign.CENTER)
        self.progress = ft.ProgressBar(visible=False, color=CYAN, bgcolor=RULE)

        # النقل اليدوي / Shizuku
        self.manual_title = ft.Text("", size=15, weight=ft.FontWeight.BOLD, color=AMBER)
        self.manual_steps = ft.Text("", size=13, color=TEXT)
        self.cmd_field = ft.TextField(
            value="",
            read_only=True,
            multiline=True,
            min_lines=3,
            max_lines=6,
            text_size=12,
            border_radius=12,
            border_color=RULE,
            bgcolor=BG,
            color=CYAN,
        )
        self.diag_note = ft.Text("", size=11.5, color=MUT, selectable=True)
        self.copy_btn = NButton("نسخ الأمر", _icon("CONTENT_COPY"), self.on_copy, kind="secondary")
        self.open_shizuku_btn = NButton(
            "فتح Shizuku / الإعدادات",
            _icon("LAUNCH"),
            self.on_open_shizuku,
            kind="secondary",
            height=46,
        )
        self.done_btn = NButton("تم التنفيذ", _icon("CHECK_CIRCLE"), self.on_manual_done)
        self.manual_panel = ft.Container(
            visible=False,
            padding=16,
            border_radius=16,
            bgcolor=_op(AMBER, 0.06),
            border=ft.Border.all(1, _op(AMBER, 0.45)),
            content=ft.Column(
                [
                    self.manual_title,
                    self.manual_steps,
                    self.cmd_field,
                    self.copy_btn.control,
                    self.open_shizuku_btn.control,
                    self.done_btn.control,
                    self.diag_note,
                ],
                spacing=10,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
        )

        self.support_btn = NButton(
            "متابعة آخر التحديثات والدعم",
            _icon("SUPPORT_AGENT"),
            kind="secondary",
            visible=False,
        )

        self.home = ft.Column(
            [
                self.quick_bar,
                self.banner,
                self.warn_banner,
                self.update_panel,
                self.activation_card,
                self.account_card,
                ft.Column(
                    [self.progress, self.status, self.speed],
                    spacing=6,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                ),
                self.manual_panel,
                self.support_btn.control,
            ],
            spacing=14,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )

        # ===== الأدوات =====
        self.diag_rows = ft.Column(spacing=8)
        self.diag_btn = NButton(
            "فحص الجاهزية والأذونات وShizuku",
            _icon("SECURITY"),
            self.on_diagnose,
        )
        self.perm_tool_btn = NButton(
            "طلب / توجيه أذونات التخزين وShizuku",
            _icon("ADMIN_PANEL_SETTINGS"),
            self.on_request_permissions,
            kind="secondary",
        )
        self.restore_btn = NButton(
            "استعادة النسخة الاحتياطية",
            _icon("RESTORE"),
            self.on_restore_backup,
            kind="secondary",
        )
        self.report_btn = NButton(
            "نسخ تقرير للدعم",
            _icon("CONTENT_COPY"),
            self.on_copy_report,
            kind="secondary",
        )
        self.recheck_btn = NButton(
            "تحديث حالة الاشتراك",
            _icon("REFRESH"),
            self.on_recheck,
            kind="secondary",
        )
        self.tools = ft.Column(
            [
                card(
                    ft.Column(
                        [
                            title("فحص الجاهزية والأذونات وShizuku", 17),
                            ft.Text(
                                "يفحص سرعة السيرفر والتخزين والأذونات وحالة Shizuku دون تعديل أي ملف.",
                                size=13,
                                color=MUT,
                            ),
                            self.diag_rows,
                            self.diag_btn.control,
                            self.perm_tool_btn.control,
                            self.report_btn.control,
                        ],
                        spacing=10,
                        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    )
                ),
                card(
                    ft.Column(
                        [
                            title("إدارة الاشتراك والنسخ الاحتياطي", 17),
                            ft.Text(
                                "حدّث حالة اشتراكك أو استعد آخر نسخة احتياطية محفوظة قبل التحديث.",
                                size=13,
                                color=MUT,
                            ),
                            self.recheck_btn.control,
                            self.restore_btn.control,
                        ],
                        spacing=10,
                        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    ),
                    accent=VIOLET,
                ),
            ],
            spacing=14,
            visible=False,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )

        # ===== السجل =====
        self.log_col = ft.Column(spacing=8)
        self.clear_log_btn = NButton(
            "مسح السجل",
            _icon("DELETE"),
            self.on_clear_log,
            kind="ghost",
            height=46,
        )
        self.logv = ft.Column(
            [
                card(
                    ft.Column(
                        [title("سجل النشاط", 17), self.log_col, self.clear_log_btn.control],
                        spacing=12,
                        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    )
                )
            ],
            spacing=14,
            visible=False,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )

        # ===== الإعدادات =====
        self.sw_auto = ft.Switch(
            value=self.auto_update,
            active_color=GREEN,
            on_change=self.on_auto_toggle,
        )
        self.sw_notif = ft.Switch(
            value=self.notifications_enabled,
            active_color=CYAN,
            on_change=self.on_notif_toggle,
        )
        self.ota_ver_text = ft.Text(self.ota_version, size=14, weight=ft.FontWeight.W_600, color=CYAN)
        self.sync_updates_btn = NButton(
            "فحص تحديثات OTA / APK",
            _icon("SYSTEM_UPDATE"),
            self.on_sync_updates,
            kind="secondary",
            height=46,
        )
        self.code_text = ft.Text("—", size=14, weight=ft.FontWeight.W_600, color=TEXT)
        self.logout_btn = NButton("تغيير الكود", _icon("LOGOUT"), self.on_logout, kind="secondary")
        self.copy_dev_btn = NButton(
            "نسخ معرّف الجهاز",
            _icon("CONTENT_COPY"),
            self.on_copy_device,
            kind="secondary",
            height=46,
        )
        self.wipe_btn = NButton(
            "مسح بيانات التطبيق",
            _icon("DELETE"),
            self.on_wipe,
            kind="danger",
            height=46,
        )
        self.settings = ft.Column(
            [
                card(
                    ft.Column(
                        [
                            title("التحديث والإشعارات", 17),
                            kv_row("إصدار OTA الحالي", self.ota_ver_text),
                            ft.Row(
                                [
                                    ft.Column(
                                        [
                                            ft.Text("تحديث الباتش تلقائياً", size=14, weight=ft.FontWeight.W_600, color=TEXT),
                                            ft.Text("يحمّل ويثبّت الباتش الجديد عند فتح التطبيق.", size=12, color=MUT),
                                        ],
                                        spacing=2,
                                        expand=True,
                                    ),
                                    self.sw_auto,
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            divider(),
                            ft.Row(
                                [
                                    ft.Column(
                                        [
                                            ft.Text("إشعارات التحقق والعمليات", size=14, weight=ft.FontWeight.W_600, color=TEXT),
                                            ft.Text("تنبيهات فورية لحالة الكود والأذونات والنقل.", size=12, color=MUT),
                                        ],
                                        spacing=2,
                                        expand=True,
                                    ),
                                    self.sw_notif,
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            self.sync_updates_btn.control,
                        ],
                        spacing=10,
                        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    )
                ),
                card(
                    ft.Column(
                        [
                            title("الحساب", 17),
                            kv_row("الكود المحفوظ", self.code_text),
                            kv_row(
                                "معرّف الجهاز",
                                ft.Text(self.device_id[:8].upper(), size=14, weight=ft.FontWeight.W_600, color=TEXT),
                            ),
                            self.copy_dev_btn.control,
                            self.logout_btn.control,
                        ],
                        spacing=10,
                        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    ),
                    accent=VIOLET,
                ),
                card(
                    ft.Column(
                        [
                            title("حول التطبيق والمطور", 17),
                            kv_row("اسم التطبيق", ft.Text(CFG.APP_TITLE, size=14, weight=ft.FontWeight.BOLD, color=CYAN)),
                            kv_row("المطور", ft.Text(CFG.DEVELOPER_NAME, size=14, weight=ft.FontWeight.BOLD, color=VIOLET)),
                            kv_row("الإصدار", ft.Text(f"v{CFG.APP_VERSION}", size=14, color=TEXT)),
                            self.wipe_btn.control,
                        ],
                        spacing=10,
                        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    ),
                    accent=PINK,
                ),
            ],
            spacing=14,
            visible=False,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )

        self.screens = [self.home, self.tools, self.logv, self.settings]
        self._tab_items: list = []

    def log(self, kind: str, msg: str) -> None:
        state.add_log(kind, msg)
        if self.tab == 2:
            self.render_log()

    def set_status(self, msg: str, color: str = MUT) -> None:
        self.status.value = msg
        self.status.color = color
        self.page.update()

    def set_busy(self, busy: bool) -> None:
        self.busy = busy
        for b in (
            self.activate_btn,
            self.install_btn,
            self.remove_btn,
            self.logout_btn,
            self.recheck_btn,
            self.wipe_btn,
            self.restore_btn,
            self.perm_quick_btn,
            self.perm_tool_btn,
            self.sync_updates_btn,
        ):
            b.set_enabled(not busy)
        self.key_input.disabled = busy
        self.progress.visible = busy
        if busy:
            self.progress.value = None
            self._last_pct = -1
        else:
            self.speed.value = ""
        self.page.update()

    def on_progress(self, value: Optional[float]) -> None:
        info = installer.progress_info
        if value is not None:
            pct = int(value * 100)
            if pct == self._last_pct:
                return
            self._last_pct = pct
            self.status.value = f"جاري تحميل الحزمة… {pct}%"
            self.status.color = CYAN
            self.speed.value = f"{_mb(info['done'])} / {_mb(info['total'])} MB  •  {_mb(info['speed'])} MB/s"
        self.progress.value = value
        self.page.update()

    def show_banner(
        self,
        text: str,
        accent: str = CYAN,
        icon_name: str = "CAMPAIGN",
        action_label: str = "",
        on_action: Optional[Callable] = None,
    ) -> None:
        self.banner_text.value = text
        self.banner_icon.name = _icon(icon_name)
        self.banner_icon.color = accent
        self.banner.bgcolor = _op(accent, 0.09)
        self.banner.border = ft.Border.all(1, _op(accent, 0.45))
        self._banner_action = on_action
        self.banner_btn.text = action_label or "إجراء"
        self.banner_btn.visible = bool(action_label and on_action is not None)
        self.banner.visible = bool(text)
        self.page.update()

    def hide_banner(self) -> None:
        self._banner_action = None
        self.banner.visible = False
        self.page.update()

    async def _on_banner_action(self, e) -> None:
        if callable(self._banner_action):
            res = self._banner_action(e)
            if inspect.isawaitable(res):
                await res

    def notify(
        self,
        kind: str,
        title_text: str,
        message: str,
        action_label: str = "",
        action_fn: Optional[Callable] = None,
        record_log: bool = True,
    ) -> None:
        palette = {
            "ok": (GREEN, "CHECK_CIRCLE"),
            "warn": (AMBER, "WARNING"),
            "err": (PINK, "ERROR"),
            "info": (CYAN, "NOTIFICATIONS_ACTIVE"),
        }
        accent, icon_name = palette.get(kind, (CYAN, "NOTIFICATIONS_ACTIVE"))
        if record_log:
            self.log(kind, f"{title_text}: {message}")
        self.status.value = f"{title_text} — {message}" if message else title_text
        self.status.color = accent
        if self.notifications_enabled:
            self.show_banner(
                f"{title_text}: {message}" if message else title_text,
                accent=accent,
                icon_name=icon_name,
                action_label=action_label,
                on_action=action_fn,
            )
        else:
            self.page.update()

    async def refresh_quick_environment(self) -> None:
        st = await asyncio.to_thread(installer.staging_dir)
        rish_ok = await asyncio.to_thread(installer.has_rish)
        present = await asyncio.to_thread(installer.is_deployed_present, self.deployed_name)
        self.shizuku_status_txt.value = "متصل (rish)" if rish_ok else "يدوي / غير متصل"
        self.shizuku_status_txt.color = GREEN if rish_ok else AMBER
        self.perm_status_txt.value = "جاهز للتجهيز" if st.shell_readable else "يحتاج إذن"
        self.perm_status_txt.color = GREEN if st.shell_readable else PINK
        if present or self.installed_version:
            self.patch_state_txt.value = f"مثبّت ({self.installed_version or 'VIP'})"
            self.patch_state_txt.color = GREEN
        else:
            self.patch_state_txt.value = "غير مثبّت"
            self.patch_state_txt.color = MUT
        self.page.update()

    async def request_permissions_and_shizuku(self) -> None:
        st = await asyncio.to_thread(installer.staging_dir)
        rish_ok = await asyncio.to_thread(installer.has_rish)
        await self.refresh_quick_environment()
        if st.shell_readable and rish_ok:
            self.notify("ok", "الأذونات وShizuku جاهزان", "مسار التجهيز متاح وخدمة Shizuku متصلة.")
        elif st.shell_readable:
            self.notify(
                "info",
                "مسار التجهيز جاهز",
                "يمكن تجهيز الملفات بنجاح؛ فعّل Shizuku للنقل التلقائي لمجلد اللعبة.",
                action_label="فتح Shizuku",
                action_fn=lambda _: asyncio.create_task(self.open_shizuku_or_settings()),
            )
        else:
            self.notify(
                "warn",
                "إذن التخزين مطلوب",
                "فعّل «إدارة كل الملفات» للتطبيق من إعدادات الهاتف ثم أعد الفحص.",
                action_label="فتح الإعدادات",
                action_fn=lambda _: asyncio.create_task(self.open_shizuku_or_settings()),
            )

    async def open_shizuku_or_settings(self) -> None:
        for uri in (
            "intent:#Intent;package=moe.shizuku.privileged.api;end",
            "android.settings.MANAGE_ALL_FILES_ACCESS_PERMISSION",
            "android.settings.SETTINGS",
        ):
            try:
                fn = getattr(self.page, "launch_url", None)
                if callable(fn):
                    out = fn(uri)
                    if inspect.isawaitable(out):
                        await out
                    self.notify("info", "تم فتح التوجيه", "أكمل التفعيل في شاشة النظام ثم ارجع إلى Lader Tareiq.")
                    return
            except Exception:
                continue
        self.notify(
            "info",
            "تفعيل الأذونات وShizuku",
            "افتح إعدادات الهاتف > التطبيقات > صلاحيات الملفات، وشغّل Shizuku ثم اضغط فحص الجاهزية.",
        )

    @guarded
    async def on_request_permissions(self, e) -> None:
        await self.request_permissions_and_shizuku()

    @guarded
    async def on_open_shizuku(self, e) -> None:
        await self.open_shizuku_or_settings()

    def _apply_ota_payload(self, payload: dict) -> None:
        if not isinstance(payload, dict):
            return
        self.ota_payload = payload
        if payload.get("support_url"):
            self.apply_support(str(payload["support_url"]))
        if payload.get("notice"):
            self.show_banner(str(payload["notice"]), accent=VIOLET, icon_name="AUTO_AWESOME")
        if payload.get("activate_label"):
            self.activate_btn.set_text(str(payload["activate_label"]))
        if payload.get("install_label") and self.license is None:
            self.install_btn.set_text(str(payload["install_label"]))

    async def sync_ota_and_app_updates(self, cfg: dict, manual: bool = False) -> bool:
        """فحص التحديث الكبير (APK) والتحديث التحسيني عن بُعد (OTA).
        تُرجع False إذا كان هناك تحديث APK إلزامي يوقف المتابعة.
        """
        cfg = cfg if isinstance(cfg, dict) else {}
        min_ver = str(cfg.get("min_app_version") or "").strip()
        update_url = str(cfg.get("update_url") or "").strip()
        if min_ver and _vt(CFG.APP_VERSION) < _vt(min_ver):
            self.show_update_required(
                cfg.get("update_message") or f"يتطلب الإصدار {min_ver} أو أحدث للمتابعة.",
                update_url,
            )
            self.notify("warn", "تحديث APK إلزامي", f"يرجى تثبيت الإصدار {min_ver}.")
            return False

        fetch_ota_fn = getattr(api, "fetch_ota_bundle", None)
        ota_res = await fetch_ota_fn(self.ota_version) if callable(fetch_ota_fn) else {}
        ota_res = ota_res if isinstance(ota_res, dict) else {}
        remote_ota = str(ota_res.get("ota_version") or cfg.get("ota_version") or "").strip()
        payload = ota_res.get("payload") if isinstance(ota_res.get("payload"), dict) else {}

        if remote_ota and _vt(remote_ota) > _vt(self.ota_version):
            self.ota_version = remote_ota
            self.ota_ver_text.value = remote_ota
            state.save(ota_version=remote_ota, ota_payload=payload)
            self._apply_ota_payload(payload)
            notes = str(payload.get("notes") or "تم تطبيق التحسينات عن بُعد بنجاح.")
            self.notify("ok", f"تحديث OTA ({remote_ota})", notes)
        elif self.ota_payload:
            self._apply_ota_payload(self.ota_payload)
        elif manual:
            latest_apk = str(cfg.get("latest_app_version") or "").strip()
            if latest_apk and _vt(latest_apk) > _vt(CFG.APP_VERSION) and update_url:
                self.notify(
                    "info",
                    f"إصدار APK جديد ({latest_apk})",
                    "يتوفر تحديث اختياري للتطبيق.",
                    action_label="تحميل APK",
                    action_fn=lambda _: self.page.launch_url(update_url),
                )
            else:
                self.notify("ok", "التطبيق محدّث", f"الإصدار {CFG.APP_VERSION} • OTA {self.ota_version}")
        return True

    @guarded
    async def on_sync_updates(self, e) -> None:
        if self.busy:
            return
        self.set_busy(True)
        try:
            self.go(0)
            self.set_status("جاري فحص تحديثات OTA وAPK…", CYAN)
            cfg = await api.fetch_app_config()
            await self.sync_ota_and_app_updates(cfg, manual=True)
        finally:
            self.set_busy(False)

    def apply_support(self, url: str) -> None:
        if url:
            self.support_url = url
        self.support_btn.set_url(self.support_url)
        self.support_btn.control.visible = bool(self.support_url)

    def set_chip(self, text: str, color: str) -> None:
        self.status_chip.content.value = text
        self.status_chip.content.color = color
        self.status_chip.border = ft.Border.all(1, _op(color, 0.7))
        self.status_chip.bgcolor = _op(color, 0.10)

    def go(self, index: int) -> None:
        self.tab = index
        for i, s in enumerate(self.screens):
            s.visible = i == index
        for i, (box, ic, lab) in enumerate(self._tab_items):
            on = i == index
            col = CYAN if on else MUT
            ic.color = col
            lab.color = col
            box.bgcolor = _op(CYAN, 0.10) if on else _op(BG, 0.0)
            box.shadow = _glow(CYAN, 14, 0.25) if on else None
        if index == 2:
            self.render_log()
        self.page.update()

    def needs_update(self) -> bool:
        lic = self.license
        return bool(
            lic
            and lic.patch_version
            and self.installed_version
            and lic.patch_version != self.installed_version
        )

    def show_update_required(self, message: str, url: str) -> None:
        self.activation_card.visible = False
        self.account_card.visible = False
        self.update_msg.value = message or "يجب تحديث APK للمتابعة."
        self.update_btn.control.visible = bool(url)
        self.update_btn.set_url(url)
        self.update_panel.visible = True
        self.set_chip("تحديث APK", AMBER)
        self.page.update()

    def show_account(self) -> None:
        self.activation_card.visible = False
        self.account_card.visible = True
        self.set_chip("نشط", GREEN)
        self.refresh_account()

    def show_activation(self) -> None:
        self.account_card.visible = False
        self.warn_banner.visible = False
        self.activation_card.visible = True
        self.set_chip("غير مفعّل", MUT)
        self.page.update()

    def refresh_account(self) -> None:
        lic = self.license
        if lic is None:
            return
        if lic.remaining_days >= 1:
            self.days_text.value = str(lic.remaining_days)
            self.days_label.value = "يوم متبقٍ"
        else:
            self.days_text.value = "<1"
            self.days_label.value = "ينتهي اليوم"
        total = lic.total_days or max(lic.remaining_days, 1)
        self.meter.value = max(0.03, min(1.0, lic.remaining_days / total))
        soon = lic.remaining_days <= 3
        self.meter.color = AMBER if soon else GREEN
        self.days_text.color = PINK if lic.remaining_days <= 1 else (AMBER if soon else CYAN)
        self.expiry_text.value = f"ينتهي في {lic.expires_at[:10]}" if lic.expires_at else ""
        self.warn_banner.visible = soon
        if soon:
            self.warn_text.value = (
                f"اشتراكك ينتهي خلال {lic.remaining_days} يوم. تواصل مع الدعم للتجديد."
                if lic.remaining_days >= 1
                else "اشتراكك ينتهي اليوم. تواصل مع الدعم للتجديد."
            )
        self.installed_text.value = f"رقم {self.installed_version}" if self.installed_version else "غير مثبّت"
        self.latest_text.value = f"رقم {lic.patch_version}" if lic.patch_version else "—"
        self.deployed_item_text.value = self.deployed_name or "—"
        outdated = self.needs_update()
        self.update_badge.visible = outdated
        self.notes_text.value = lic.patch_notes
        self.notes_box.visible = bool(lic.patch_notes)
        self.install_btn.set_text(
            "تحديث الباتش"
            if outdated
            else ("إعادة تثبيت الباتش" if self.installed_version else "تثبيت الباتش")
        )
        key = state.load().get("key") or ""
        self.code_text.value = ("••••" + key[-4:]) if len(key) >= 4 else "—"
        self.patch_state_txt.value = (
            f"مثبّت ({self.installed_version or 'VIP'})" if self.installed_version else "غير مثبّت"
        )
        self.patch_state_txt.color = GREEN if self.installed_version else MUT
        self.page.update()

    def mark_installed(self, version: str, deployed_name: str = "") -> None:
        self.installed_version = version or ""
        self.deployed_name = deployed_name or ""
        state.save(installed_version=version or None, deployed_name=deployed_name or None)
        self.refresh_account()

    def show_manual(self, command: str, kind: str) -> None:
        self._manual_kind = kind
        self.cmd_field.value = command
        if kind == "remove":
            self.manual_title.value = "حذف الباتش/المجلد عبر Shizuku أو يدوياً"
            self.manual_steps.value = (
                "١) افتح طرفية Shizuku (مثل aShell You)\n"
                "٢) الصق الأمر التالي ونفّذه\n"
                "٣) ارجع هنا واضغط «تم التنفيذ»"
            )
        else:
            self.manual_title.value = "الحزمة جاهزة — أكمل النقل عبر Shizuku"
            self.manual_steps.value = (
                "١) افتح طرفية Shizuku (مثل aShell You)\n"
                "٢) الصق الأمر التالي ونفّذه\n"
                "٣) تأكد من ظهور الملفات في الوجهة، ثم اضغط «تم التنفيذ»"
            )
        st = installer.last_staging
        if kind == "remove" or st is None:
            self.diag_note.value = ""
        elif st.shell_readable:
            self.diag_note.value = f"📁 مجلد التجهيز: {st.path}"
            self.diag_note.color = MUT
        else:
            self.diag_note.value = (
                "⚠️ تعذر الحفظ في مسار يقرؤه Shizuku.\n"
                "فعّل: الإعدادات ← التطبيقات ← الأذونات ← الملفات ← السماح بإدارة كل الملفات، ثم أعد المحاولة.\n"
                + "\n".join(st.notes)
            )
            self.diag_note.color = PINK
        self.manual_panel.visible = True
        self.page.update()

    def hide_manual(self) -> None:
        self.manual_panel.visible = False
        self.page.update()

    async def _copy(self, text: str) -> bool:
        try:
            if self._clip is None:
                self._clip = ft.Clipboard()
                self.page.services.append(self._clip)
            await self._clip.set(text)
            return True
        except Exception:
            try:
                self.page.set_clipboard(text)
                return True
            except Exception:
                return False

    @guarded
    async def on_copy(self, e) -> None:
        ok = await self._copy(self.cmd_field.value or "")
        self.notify(
            "ok" if ok else "warn",
            "نسخ الأمر",
            "تم نسخ أمر Shizuku بنجاح." if ok else "تعذر النسخ التلقائي؛ انسخ الأمر مطولاً.",
            record_log=False,
        )

    @guarded
    async def on_manual_done(self, e) -> None:
        if self._manual_kind == "remove":
            self.mark_installed("", "")
            self.notify("ok", "تم حذف الباتش", "تم تأكيد إزالة الباتش/المجلد عبر Shizuku.")
        else:
            dname = self._staged.name if self._staged else ""
            self.mark_installed(self.license.patch_version if self.license else "", dname)
            installer.cleanup(self._staged)
            self._staged = None
            self.notify("ok", "تم التثبيت", f"تم تثبيت {dname or self.installed_version}؛ يمكنك تشغيل اللعبة الآن.")
        self.hide_manual()

    @guarded
    async def start(self) -> None:
        self.render_log()
        await self.refresh_quick_environment()
        cfg = await api.fetch_app_config()
        if isinstance(cfg, dict) and cfg.get("support_url"):
            self.apply_support(str(cfg.get("support_url") or ""))
        if isinstance(cfg, dict) and cfg.get("notice"):
            self.show_banner(str(cfg.get("notice") or ""), accent=CYAN, icon_name="CAMPAIGN")
        if not await self.sync_ota_and_app_updates(cfg if isinstance(cfg, dict) else {}, manual=False):
            return

        saved = state.load().get("key") or ""
        if not saved:
            self.page.update()
            return
        self.key_input.value = saved
        self.set_busy(True)
        try:
            self.set_status("جاري التحقق التلقائي من اشتراكك…", CYAN)
            ok = await self.verify(saved, auto=True)
            lic = self.license
            if ok and lic and self.needs_update():
                self.notify("info", "تحديث باتش جديد", f"يتوفر إصدار جديد رقم {lic.patch_version}.")
                if lic.force_update or self.auto_update:
                    self.set_status("جاري التحديث تلقائياً…", CYAN)
                    await self.do_install()
        finally:
            self.set_busy(False)

    async def verify(self, key: str, auto: bool = False) -> bool:
        result = await api.verify_license(key)
        S = api.LicenseStatus
        if result.status is S.ACTIVE:
            self.license = result
            state.save(key=key)
            if result.notice:
                self.show_banner(result.notice, accent=VIOLET, icon_name="CAMPAIGN")
            self.apply_support(result.support_url)
            self.show_account()
            days_txt = f"متبقي {result.remaining_days} يوم" if result.remaining_days >= 1 else "ينتهي اليوم"
            self.notify("ok", "تم التحقق من الكود", f"اشتراكك نشط ({days_txt}).")
            return True
        if result.status is S.UPDATE_REQUIRED:
            self.show_update_required(result.message, result.update_url)
            self.notify("warn", "تحديث APK مطلوب", result.message or "يلزم تحديث التطبيق للمتابعة.")
            return False
        if result.status is S.MAINTENANCE:
            self.show_banner(result.message, accent=AMBER, icon_name="CONSTRUCTION")
            self.notify("warn", "وضع الصيانة", result.message or "السيرفر تحت الصيانة حالياً.")
        if result.status is S.INVALID:
            state.save(key=None)
        self.show_activation()
        if result.status in (S.NETWORK_ERROR, S.SERVER_ERROR):
            if not auto:
                self.notify("warn", "تعذر التحقق", result.message or "تحقق من اتصال الإنترنت.")
            else:
                self.set_status(result.message or "تعذر التحقق التلقائي من الشبكة.", AMBER)
        else:
            self.notify("err", "تنبيه الكود", result.message or "الكود غير صالح أو منتهي.")
        return False

    @guarded
    async def on_activate(self, e) -> None:
        if self.busy:
            return
        key = (self.key_input.value or "").strip()
        if not key:
            self.notify("warn", "إدخال مطلوب", "الرجاء كتابة كود التفعيل أولاً.")
            return
        self.set_busy(True)
        try:
            self.set_status("جاري التحقق من كود التفعيل…", CYAN)
            if await self.verify(key):
                if not self.installed_version:
                    self.set_status("الكود صالح! جاري تحميل وتجهيز الحزمة…", CYAN)
                    await self.do_install()
        finally:
            self.set_busy(False)

    @guarded
    async def on_install(self, e) -> None:
        if self.busy or self.license is None:
            return
        self.set_busy(True)
        try:
            key = state.load().get("key") or (self.key_input.value or "").strip()
            if key and not await self.verify(key):
                return
            await self.do_install()
        finally:
            self.set_busy(False)

    @guarded
    async def on_recheck(self, e) -> None:
        if self.busy:
            return
        key = state.load().get("key") or ""
        if not key:
            self.go(0)
            self.notify("warn", "لا يوجد كود محفوظ", "أدخل كود التفعيل أولاً.")
            return
        self.set_busy(True)
        try:
            self.go(0)
            self.set_status("جاري تحديث حالة الاشتراك…", CYAN)
            if await self.verify(key) and self.needs_update():
                self.notify("info", "تحديث متاح", "يوجد إصدار باتش جديد؛ اضغط «تحديث الباتش».")
        finally:
            self.set_busy(False)

    async def do_install(self) -> None:
        lic = self.license
        if lic is None:
            return
        if not (lic.download_url or CFG.PATCH_DOWNLOAD_URL or CFG.PATCH_MIRRORS):
            self.notify("warn", "الرابط غير متوفر", "لم يضف المشرف رابط الباتش بعد؛ تواصل مع الدعم.")
            return
        self.hide_manual()
        installer.configure_target(lic.target_file_name, lic.game_package)
        staged = None
        keep_file = False
        try:
            self.set_status("جاري تحميل الحزمة…", CYAN)
            staged = await installer.download_patch(
                self.on_progress,
                lic.download_url,
                lic.patch_sha256,
                lic.deploy_mode,
            )
            self.progress.value = None
            self.set_status("تم التجهيز! جاري النقل إلى مجلد اللعبة…", CYAN)
            res = await installer.install_patch(staged)
            self.mark_installed(lic.patch_version, res.deployed_name)
            await self.refresh_quick_environment()
            how = "عبر Shizuku" if res.method == "shizuku" else "مباشرة"
            what = f"المجلد '{res.deployed_name}'" if res.kind == "folder" else f"الباتش {lic.patch_version}"
            self.notify("ok", "تم التثبيت بنجاح", f"تم نقل {what} {how}؛ يمكنك فتح اللعبة الآن.")
        except installer.InstallError as ex:
            if ex.manual_command:
                keep_file = True
                self._staged = staged
                self.notify(
                    "warn",
                    "نقل عبر Shizuku مطلوب",
                    "تم تجهيز الملف؛ انسخ أمر Shizuku ونفّذه لإكمال النقل.",
                    action_label="فتح Shizuku",
                    action_fn=lambda _: asyncio.create_task(self.open_shizuku_or_settings()),
                )
                self.show_manual(ex.manual_command, "install")
            else:
                self.notify("err", "فشل التثبيت", str(ex))
        finally:
            if not keep_file:
                installer.cleanup(staged)

    async def _confirm_twice(self, name: str, btn: NButton, normal: str, confirm: str) -> bool:
        base_kind = "secondary" if name == "remove" else "danger"
        task = self._armed.get(name)
        if task is None:
            btn.set_text(confirm)
            btn.apply_kind("danger")

            async def disarm_later() -> None:
                try:
                    await asyncio.sleep(4)
                except asyncio.CancelledError:
                    return
                self._armed.pop(name, None)
                btn.set_text(normal)
                btn.apply_kind(base_kind)
                self.page.update()

            self._armed[name] = asyncio.create_task(disarm_later())
            self.page.update()
            return False
        task.cancel()
        self._armed.pop(name, None)
        btn.set_text(normal)
        btn.apply_kind(base_kind)
        return True

    @guarded
    async def on_remove_click(self, e) -> None:
        if self.busy:
            return
        if not await self._confirm_twice(
            "remove",
            self.remove_btn,
            "حذف الباتش",
            "اضغط مرة أخرى لتأكيد الحذف",
        ):
            return
        self.set_busy(True)
        try:
            await self.do_remove()
        finally:
            self.set_busy(False)

    async def do_remove(self) -> None:
        lic = self.license
        installer.configure_target(
            lic.target_file_name if lic else "",
            lic.game_package if lic else "",
        )
        self.hide_manual()
        target_item = self.deployed_name
        try:
            self.set_status("جاري الحذف من مجلد اللعبة…", CYAN)
            res = await installer.remove_patch(target_item)
            self.mark_installed("", "")
            await self.refresh_quick_environment()
            how = "عبر Shizuku" if res.method == "shizuku" else "مباشرة"
            self.notify("ok", "تم الحذف", f"تمت إزالة الباتش {how}.")
        except installer.InstallError as ex:
            self.notify(
                "warn",
                "الحذف عبر Shizuku مطلوب",
                str(ex),
                action_label="فتح Shizuku",
                action_fn=lambda _: asyncio.create_task(self.open_shizuku_or_settings()),
            )
            self.show_manual(ex.manual_command, "remove")

    @guarded
    async def on_restore_backup(self, e) -> None:
        if self.busy:
            return
        self.set_busy(True)
        try:
            self.go(0)
            self.set_status("جاري استعادة النسخة الاحتياطية…", CYAN)
            res = await installer.restore_backup(self.deployed_name)
            await self.refresh_quick_environment()
            how = "عبر Shizuku" if res.method == "shizuku" else "مباشرة"
            self.notify("ok", "تمت الاستعادة", f"تمت استعادة النسخة الاحتياطية {how}.")
        except installer.InstallError as ex:
            self.notify("err", "تعذر الاستعادة", str(ex))
        finally:
            self.set_busy(False)

    @guarded
    async def on_diagnose(self, e) -> None:
        if self.busy:
            return
        self.diag_btn.set_enabled(False)
        self.diag_rows.controls = [ft.Text("جاري الفحص…", size=13, color=CYAN)]
        self.page.update()
        try:
            online, ping_ms = await api.ping_server()
            lic = self.license
            installer.configure_target(
                lic.target_file_name if lic else "",
                lic.game_package if lic else "",
            )
            rows = [
                (
                    "الاتصال بالسيرفر",
                    "ok" if online else "warn",
                    f"متصل ({ping_ms} ms)" if online else "تعذر الوصول للسيرفر",
                ),
                (
                    "الاشتراك",
                    "ok" if lic else "info",
                    f"نشط، متبقي {lic.remaining_days} يوم" if lic else "غير مفعّل",
                ),
            ]
            if lic:
                has_url = bool(lic.download_url or CFG.PATCH_DOWNLOAD_URL)
                rows.append(
                    (
                        "رابط الحزمة",
                        "ok" if has_url else "warn",
                        "مضبوط" if has_url else "لم يضفه المشرف بعد",
                    )
                )
            rows += await asyncio.to_thread(installer.diagnostics)
            self._diag = rows
            colors = {"ok": GREEN, "warn": AMBER, "info": MUT}
            icons = {"ok": _icon("CHECK_CIRCLE"), "warn": _icon("WARNING"), "info": _icon("INFO")}
            self.diag_rows.controls = [
                ft.Row(
                    [
                        ft.Icon(icons[s], size=20, color=colors[s]),
                        ft.Column(
                            [
                                ft.Text(label, size=13.5, weight=ft.FontWeight.W_600, color=TEXT),
                                ft.Text(detail, size=12, color=MUT),
                            ],
                            spacing=0,
                            expand=True,
                        ),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                )
                for label, s, detail in rows
            ]
            await self.refresh_quick_environment()
            self.notify("info", "اكتمل الفحص", f"زمن الاستجابة: {ping_ms} ms.")
        finally:
            self.diag_btn.set_enabled(True)
            self.page.update()

    @guarded
    async def on_copy_report(self, e) -> None:
        lic = self.license
        lines = [
            f"{CFG.APP_TITLE} v{CFG.APP_VERSION} (OTA {self.ota_version}) • {CFG.DEVELOPER_TAGLINE}",
            f"الجهاز: {self.device_id[:8].upper()}",
            f"الاشتراك: {'نشط (' + str(lic.remaining_days) + ' يوم)' if lic else 'غير مفعّل'}",
            f"الإصدار المثبّت: {self.installed_version or '—'} | العنصر: {self.deployed_name or '—'}",
        ]
        for label, s, detail in self._diag:
            lines.append(f"[{s}] {label}: {detail}")
        for ent in state.get_log()[-8:]:
            lines.append(f"{ent.get('t', '')[:16]} {ent.get('m', '')}")
        ok = await self._copy("\n".join(lines))
        self.go(0)
        self.notify(
            "ok" if ok else "warn",
            "تقرير التشخيص",
            "تم نسخ التقرير؛ أرسله للدعم." if ok else "تعذر النسخ التلقائي.",
            record_log=False,
        )

    def render_log(self) -> None:
        entries = list(reversed(state.get_log()))
        colors = {"ok": GREEN, "err": PINK, "warn": AMBER, "info": CYAN}
        if not entries:
            self.log_col.controls = [ft.Text("لا توجد أحداث بعد.", size=13, color=MUT)]
        else:
            rows = []
            for ent in entries[:40]:
                try:
                    stamp = datetime.strptime(ent["t"], "%Y-%m-%dT%H:%M:%SZ").strftime("%m-%d %H:%M")
                except (KeyError, ValueError):
                    stamp = ""
                col = colors.get(ent.get("k"), MUT)
                rows.append(
                    ft.Row(
                        [
                            ft.Container(
                                width=8,
                                height=8,
                                border_radius=99,
                                bgcolor=col,
                                shadow=_glow(col, 8, 0.8),
                                margin=6,
                            ),
                            ft.Column(
                                [
                                    ft.Text(ent.get("m", ""), size=13.5, color=TEXT),
                                    ft.Text(stamp + " UTC", size=11, color=MUT),
                                ],
                                spacing=0,
                                expand=True,
                            ),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    )
                )
            self.log_col.controls = rows
        try:
            self.page.update()
        except Exception:
            pass

    @guarded
    async def on_clear_log(self, e) -> None:
        state.save(log=None)
        self.render_log()

    @guarded
    async def on_auto_toggle(self, e) -> None:
        self.auto_update = bool(self.sw_auto.value)
        state.save(auto_update=self.auto_update)

    @guarded
    async def on_notif_toggle(self, e) -> None:
        self.notifications_enabled = bool(self.sw_notif.value)
        state.save(notifications_enabled=self.notifications_enabled)

    @guarded
    async def on_copy_device(self, e) -> None:
        ok = await self._copy(self.device_id)
        self.go(0)
        self.notify(
            "ok" if ok else "warn",
            "معرّف الجهاز",
            "تم نسخ معرّف الجهاز بنجاح." if ok else "تعذر النسخ التلقائي.",
            record_log=False,
        )

    @guarded
    async def on_logout(self, e) -> None:
        if self.busy:
            return
        state.save(key=None)
        self.license = None
        self.key_input.value = ""
        self.code_text.value = "—"
        self.hide_manual()
        self.show_activation()
        self.go(0)
        self.notify("info", "تم تسجيل الخروج", "تمت إزالة كود التفعيل من هذا الجهاز.")

    @guarded
    async def on_wipe(self, e) -> None:
        if self.busy:
            return
        if not await self._confirm_twice(
            "wipe",
            self.wipe_btn,
            "مسح بيانات التطبيق",
            "اضغط مرة أخرى لتأكيد المسح",
        ):
            return
        state.save(
            key=None,
            installed_version=None,
            deployed_name=None,
            log=None,
            auto_update=None,
            notifications_enabled=None,
            ota_version=None,
            ota_payload=None,
        )
        self.license = None
        self.installed_version = ""
        self.deployed_name = ""
        self.auto_update = False
        self.notifications_enabled = True
        self.ota_version = getattr(CFG, "OTA_VERSION", "1.0.0")
        self.ota_payload = {}
        self.ota_ver_text.value = self.ota_version
        self.sw_auto.value = False
        self.sw_notif.value = True
        self.key_input.value = ""
        self.code_text.value = "—"
        self.hide_manual()
        await self.refresh_quick_environment()
        self.show_activation()
        self.go(0)
        self.notify("ok", "تم مسح البيانات", "تمت إعادة ضبط بيانات تطبيق Lader Tareiq.", record_log=False)

    def build(self) -> ft.Control:
        specs = [
            ("الرئيسية", "HOME"),
            ("الأدوات", "HANDYMAN"),
            ("السجل", "HISTORY"),
            ("الإعدادات", "SETTINGS"),
        ]
        items = []
        for i, (label, ic_name) in enumerate(specs):
            ic = ft.Icon(_icon(ic_name), size=22, color=MUT)
            lab = ft.Text(label, size=11.5, color=MUT, weight=ft.FontWeight.W_600)
            box = ft.Container(
                content=ft.Column([ic, lab], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=8,
                border_radius=14,
                expand=True,
                alignment=ft.Alignment.CENTER,
                ink=True,
                on_click=lambda e, idx=i: self.go(idx),
            )
            items.append((box, ic, lab))
        self._tab_items = items
        tabbar = ft.Container(
            content=ft.Row([b for b, _, _ in items], spacing=4),
            padding=8,
            bgcolor=_op(PLATE, 0.96),
            border=ft.Border.all(1, _op(CYAN, 0.20)),
        )
        body = ft.Container(
            content=ft.Column(
                self.screens,
                scroll=ft.ScrollMode.AUTO,
                expand=True,
                spacing=0,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
            padding=16,
            expand=True,
        )
        root = ft.Container(
            content=ft.Column([self.header, body, tabbar], spacing=0, expand=True),
            expand=True,
            gradient=_grad(BG, BG2, vertical=True),
            bgcolor=None if _grad(BG, BG2) is not None else BG,
        )
        for i, (box, ic, lab) in enumerate(items):
            on = i == 0
            ic.color = CYAN if on else MUT
            lab.color = CYAN if on else MUT
            box.bgcolor = _op(CYAN, 0.10) if on else _op(BG, 0.0)
            box.shadow = _glow(CYAN, 14, 0.25) if on else None
        self.home.visible = True
        return ft.SafeArea(content=root, expand=True)


async def main(page: ft.Page) -> None:
    page.title = f"{CFG.APP_TITLE} — {CFG.DEVELOPER_NAME}"
    page.theme_mode = ft.ThemeMode.DARK
    _safe(lambda: setattr(page, "theme", ft.Theme(color_scheme_seed=CYAN)))
    page.bgcolor = BG
    page.padding = 0
    _safe(
        lambda: setattr(
            page,
            "locale_configuration",
            ft.LocaleConfiguration(
                supported_locales=[ft.Locale("ar"), ft.Locale("en")],
                current_locale=ft.Locale("ar"),
            ),
        )
    )
    try:
        view = App(page)
        page.add(view.build())
    except Exception:
        page.add(
            ft.SafeArea(
                content=ft.Container(
                    padding=16,
                    content=ft.Column(
                        [
                            ft.Text("تعذر تشغيل الواجهة", size=18, color=PINK, weight=ft.FontWeight.BOLD),
                            ft.Text(traceback.format_exc(), size=11, color=TEXT, selectable=True),
                        ],
                        scroll=ft.ScrollMode.AUTO,
                    ),
                    expand=True,
                ),
                expand=True,
            )
        )
        return
    await view.start()


if __name__ == "__main__":
    runner = getattr(ft, "run", None) or getattr(ft, "app", None)
    runner(main)
