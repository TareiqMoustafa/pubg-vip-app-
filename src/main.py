"""نقطة الدخول الرئيسية لتطبيق Lader Tareiq (Flet)."""
from __future__ import annotations

import threading
from typing import Any

import flet as ft

from api import (
    check_health,
    fetch_app_config,
    fetch_ota_bundle,
    get_device_id,
    is_newer_version,
    verify_license,
)
from config import (
    APP_TITLE,
    APP_VERSION,
    COLOR_AMBER,
    COLOR_BG,
    COLOR_BG_ALT,
    COLOR_CARD_BORDER,
    COLOR_CYAN,
    COLOR_GREEN,
    COLOR_MUTED,
    COLOR_PINK,
    COLOR_TEXT,
    COLOR_VIOLET,
    DEFAULT_DEPLOY_MODE,
    DEFAULT_GAME_PACKAGE,
    DEFAULT_SUPPORT_URL,
    DEFAULT_TARGET_FILE,
    DEVELOPER_NAME,
    DEVELOPER_TAGLINE,
)
from installer import download_and_prepare
from state import add_log, clear_logs, load as load_state, save as save_state
from ui_components import build_metric_tile, build_section_card, status_palette


def main(page: ft.Page) -> None:
    page.title = APP_TITLE
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = COLOR_BG
    page.padding = 0
    page.scroll = None

    try:
        page.rtl = True
    except Exception:
        pass

    state: dict[str, Any] = load_state()
    device_id: str = get_device_id()
    busy_lock = threading.Lock()
    is_busy = False

    notice_banner_text = ft.Text(
        state.get("notice") or f"مرحباً بك في {APP_TITLE} — جاهز للتحقق والمزامنة.",
        size=12.5,
        color=COLOR_TEXT,
        expand=True,
    )
    notice_banner = ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(
                    getattr(ft.Icons, "CAMPAIGN_OUTLINED", None) or getattr(ft.Icons, "INFO", None),
                    color=COLOR_CYAN,
                    size=18,
                ),
                notice_banner_text,
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
        border_radius=12,
        bgcolor="#0C1633",
        border=ft.border.all(1, "#1F356E"),
        visible=bool(state.get("notice")),
    )

    status_badge = ft.Container(
        content=ft.Text("غير مفعّل", size=12, weight=ft.FontWeight.BOLD),
        padding=ft.padding.symmetric(horizontal=12, vertical=5),
        border_radius=99,
    )
    status_message_txt = ft.Text(
        state.get("license_message") or "أدخل كود التفعيل للتحقق وتجهيز الحزمة.",
        size=13,
        color=COLOR_MUTED,
    )

    metric_days = build_metric_tile("الأيام المتبقية", "0", COLOR_GREEN)
    metric_patch = build_metric_tile("إصدار الباتش", "-", COLOR_CYAN)
    metric_ota = build_metric_tile("إصدار OTA", str(state.get("ota_version") or "1.0.0"), COLOR_VIOLET)

    key_input = ft.TextField(
        label="كود التفعيل (License Key)",
        hint_text="LT-XXXX-YYYY-ZZZZ",
        value=str(state.get("license_key") or ""),
        border_radius=12,
        bgcolor="#060914",
        border_color=COLOR_CARD_BORDER,
        focused_border_color=COLOR_CYAN,
        text_size=14,
    )

    progress_bar = ft.ProgressBar(
        value=0.0,
        color=COLOR_CYAN,
        bgcolor="#111A36",
        visible=False,
    )
    progress_label = ft.Text("", size=12, color=COLOR_MUTED, visible=False)

    patch_info_txt = ft.Text(
        "لا توجد حزمة محمّلة بعد.",
        size=12.5,
        color=COLOR_MUTED,
    )

    update_alert_body = ft.Text("", size=12.5, color=COLOR_TEXT)
    update_alert_card = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(
                    "يتوفر تحديث جديد للتطبيق",
                    size=14,
                    weight=ft.FontWeight.BOLD,
                    color=COLOR_AMBER,
                ),
                update_alert_body,
            ],
            spacing=4,
        ),
        padding=12,
        border_radius=12,
        bgcolor="#1E180A",
        border=ft.border.all(1, COLOR_AMBER),
        visible=False,
    )

    ota_notes_txt = ft.Text(
        "لا توجد ملاحظات OTA جديدة حالياً.",
        size=12.5,
        color=COLOR_MUTED,
    )

    auto_update_switch = ft.Switch(
        label="تحديث تلقائي عند التشغيل",
        value=bool(state.get("auto_update", True)),
        active_color=COLOR_CYAN,
    )
    notifications_switch = ft.Switch(
        label="تسجيل التنبيهات في السجل",
        value=bool(state.get("notifications_enabled", True)),
        active_color=COLOR_VIOLET,
    )
    device_id_txt = ft.Text(f"معرّف الجهاز: {device_id}", size=12, color=COLOR_MUTED)
    app_ver_txt = ft.Text(f"نسخة التطبيق: {APP_VERSION}", size=12, color=COLOR_MUTED)
    logs_column = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO)

    activate_btn = ft.ElevatedButton(
        text="تحقق وفعّل",
        on_click=lambda _: _start_bg(_on_verify_click),
        style=ft.ButtonStyle(
            bgcolor=COLOR_CYAN,
            color="#031318",
            padding=ft.padding.symmetric(horizontal=18, vertical=12),
            shape=ft.RoundedRectangleBorder(radius=12),
            text_style=ft.TextStyle(weight=ft.FontWeight.BOLD),
        ),
    )
    install_btn = ft.ElevatedButton(
        text="تحميل وتجهيز الحزمة",
        on_click=lambda _: _start_bg(_on_download_click),
        style=ft.ButtonStyle(
            bgcolor=COLOR_VIOLET,
            color="#FFFFFF",
            padding=ft.padding.symmetric(horizontal=18, vertical=12),
            shape=ft.RoundedRectangleBorder(radius=12),
            text_style=ft.TextStyle(weight=ft.FontWeight.BOLD),
        ),
    )
    sync_btn = ft.OutlinedButton(
        text="فحص تحديثات OTA / APK",
        on_click=lambda _: _start_bg(lambda: _sync_remote(manual=True)),
        style=ft.ButtonStyle(
            color=COLOR_CYAN,
            side=ft.BorderSide(1, COLOR_CYAN),
            padding=ft.padding.symmetric(horizontal=16, vertical=11),
            shape=ft.RoundedRectangleBorder(radius=12),
        ),
    )

    def _show_snack(msg: str) -> None:
        try:
            page.snack_bar = ft.SnackBar(
                content=ft.Text(msg, color=COLOR_TEXT),
                bgcolor="#0E1733",
            )
            page.snack_bar.open = True
            page.update()
        except Exception:
            pass

    def _set_busy(val: bool) -> None:
        nonlocal is_busy
        with busy_lock:
            is_busy = val
        activate_btn.disabled = val
        install_btn.disabled = val
        sync_btn.disabled = val

    def _update_metric_value(tile: ft.Container, new_val: str) -> None:
        try:
            col = tile.content
            if isinstance(col, ft.Column) and len(col.controls) >= 1 and isinstance(col.controls[0], ft.Text):
                col.controls[0].value = new_val
        except Exception:
            pass

    def _refresh_logs_ui() -> None:
        items = state.get("logs") or []
        if not items:
            logs_column.controls = [
                ft.Container(
                    content=ft.Text("لا توجد سجلات بعد.", size=12.5, color=COLOR_MUTED),
                    padding=14,
                    border_radius=12,
                    bgcolor="#080D1E",
                )
            ]
            return

        kind_colors = {
            "success": COLOR_GREEN,
            "error": COLOR_PINK,
            "warn": COLOR_AMBER,
            "ota": COLOR_VIOLET,
        }
        cards: list[ft.Control] = []
        for entry in reversed(items[-40:]):
            k = str(entry.get("kind") or "info").lower()
            c = kind_colors.get(k, COLOR_CYAN)
            cards.append(
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Text(k.upper(), size=11, weight=ft.FontWeight.BOLD, color=c),
                                    ft.Text(str(entry.get("time") or ""), size=11, color=COLOR_MUTED),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            ft.Text(str(entry.get("message") or ""), size=12.5, color=COLOR_TEXT),
                        ],
                        spacing=4,
                    ),
                    padding=12,
                    border_radius=12,
                    bgcolor="#080D1E",
                    border=ft.border.all(1, "#172347"),
                )
            )
        logs_column.controls = cards

    def _refresh_ui() -> None:
        nonlocal state
        state = load_state()

        st_code = str(state.get("license_status") or "inactive")
        pal_color, pal_label = status_palette(st_code)
        badge_txt = status_badge.content
        if isinstance(badge_txt, ft.Text):
            badge_txt.value = pal_label
            badge_txt.color = pal_color
        status_badge.bgcolor = "#101936"
        status_badge.border = ft.border.all(1, pal_color)

        status_message_txt.value = str(state.get("license_message") or "")
        _update_metric_value(metric_days, str(state.get("remaining_days") or 0))
        _update_metric_value(
            metric_patch,
            str(state.get("latest_patch_version") or state.get("installed_patch_version") or "-"),
        )
        _update_metric_value(metric_ota, str(state.get("ota_version") or "1.0.0"))

        notice_str = str(state.get("notice") or "").strip()
        notice_banner_text.value = notice_str
        notice_banner.visible = bool(notice_str)

        payload = state.get("ota_payload") if isinstance(state.get("ota_payload"), dict) else {}
        if payload.get("activate_label"):
            activate_btn.text = str(payload["activate_label"])
        if payload.get("install_label"):
            install_btn.text = str(payload["install_label"])
        ota_notes_txt.value = str(
            payload.get("notes") or state.get("patch_notes") or "لا توجد ملاحظات إضافية حالياً."
        )

        dl_url = str(state.get("download_url") or "").strip()
        file_nm = str(state.get("target_file_name") or DEFAULT_TARGET_FILE)
        mode_nm = str(state.get("deploy_mode") or DEFAULT_DEPLOY_MODE)
        inst_ver = str(state.get("installed_patch_version") or "غير مثبت")
        if dl_url:
            patch_info_txt.value = (
                f"الملف: {file_nm} | النمط: {mode_nm} | المثبّت: {inst_ver}\n"
                "رابط الحزمة جاهز للتحميل والتحقق."
            )
        else:
            patch_info_txt.value = (
                f"النمط الافتراضي: {mode_nm} | المثبّت: {inst_ver}\n"
                "فعّل الكود أولاً لاستلام رابط الحزمة من السيرفر."
            )

        latest_apk = str(state.get("latest_app_version") or "").strip()
        upd_msg = str(state.get("update_message") or "").strip()
        upd_url = str(state.get("update_url") or "").strip()
        if latest_apk and is_newer_version(latest_apk, APP_VERSION):
            update_alert_card.visible = True
            base_line = upd_msg or f"يتوفر إصدار APK أحدث ({latest_apk}) من نسختك الحالية ({APP_VERSION})."
            update_alert_body.value = base_line + (f"\nالرابط: {upd_url}" if upd_url else "")
        else:
            update_alert_card.visible = False

        auto_update_switch.value = bool(state.get("auto_update", True))
        notifications_switch.value = bool(state.get("notifications_enabled", True))
        device_id_txt.value = f"معرّف الجهاز: {device_id}"
        app_ver_txt.value = f"نسخة التطبيق: {APP_VERSION}"

        _refresh_logs_ui()
        try:
            page.update()
        except Exception:
            pass

    def _record_event(kind: str, msg: str) -> None:
        if state.get("notifications_enabled", True) or kind == "error":
            add_log(kind, msg)

    def _sync_remote(manual: bool = False) -> None:
        _set_busy(True)
        try:
            cfg_res = fetch_app_config()
            if cfg_res.ok:
                d = cfg_res.data
                updates: dict[str, Any] = {
                    "maintenance": bool(d.get("maintenance", False)),
                    "notice": str(d.get("notice") or state.get("notice") or ""),
                    "support_url": str(d.get("support_url") or state.get("support_url") or DEFAULT_SUPPORT_URL),
                    "latest_app_version": str(d.get("latest_app_version") or ""),
                    "update_url": str(d.get("update_url") or ""),
                    "update_message": str(d.get("update_message") or ""),
                    "deploy_mode": str(d.get("deploy_mode") or state.get("deploy_mode") or DEFAULT_DEPLOY_MODE),
                }
                if d.get("patch_version"):
                    updates["latest_patch_version"] = str(d["patch_version"])
                save_state(**updates)

                remote_ota_ver = str(d.get("ota_version") or "").strip()
                local_ota_ver = str(state.get("ota_version") or "1.0.0").strip()
                if remote_ota_ver and (manual or is_newer_version(remote_ota_ver, local_ota_ver) or remote_ota_ver != local_ota_ver):
                    ota_res = fetch_ota_bundle(remote_ota_ver)
                    if ota_res.ok:
                        ota_payload = ota_res.data.get("payload") or {}
                        save_state(
                            ota_version=str(ota_res.data.get("ota_version") or remote_ota_ver),
                            ota_payload=ota_payload,
                            notice=str(ota_payload.get("notice") or updates["notice"]),
                            support_url=str(ota_payload.get("support_url") or updates["support_url"]),
                        )
                        _record_event("ota", f"تمت مزامنة حزمة OTA الإصدار {remote_ota_ver}.")
                    else:
                        _record_event("warn", f"تعذر التحقق من OTA: {ota_res.message}")

                if manual:
                    _record_event("success", "تم فحص إعدادات التطبيق وOTA بنجاح.")
                    _show_snack("تمت مزامنة الإعدادات بنجاح.")
            else:
                if manual:
                    _record_event("warn", cfg_res.message)
                    _show_snack(cfg_res.message)
        finally:
            _set_busy(False)
            _refresh_ui()

    def _on_verify_click() -> None:
        _set_busy(True)
        try:
            entered_key = str(key_input.value or "").strip().upper()
            res = verify_license(entered_key, device_id=device_id, app_version=APP_VERSION)
            d = res.data
            st_val = str(d.get("status") or ("active" if res.ok else "inactive"))

            if res.ok and st_val == "active":
                save_state(
                    license_key=entered_key,
                    license_status="active",
                    license_message=res.message,
                    license_type=str(d.get("type") or ""),
                    expires_at=str(d.get("expires_at") or ""),
                    remaining_days=int(d.get("remaining_days") or 0),
                    remaining_hours=int(d.get("remaining_hours") or 0),
                    total_days=int(d.get("total_days") or 0),
                    latest_patch_version=str(d.get("patch_version") or ""),
                    download_url=str(d.get("download_url") or ""),
                    target_file_name=str(d.get("target_file_name") or DEFAULT_TARGET_FILE),
                    game_package=str(d.get("game_package") or DEFAULT_GAME_PACKAGE),
                    deploy_mode=str(d.get("deploy_mode") or DEFAULT_DEPLOY_MODE),
                    patch_sha256=str(d.get("patch_sha256") or ""),
                    patch_notes=str(d.get("patch_notes") or ""),
                    force_patch_update=bool(d.get("force_update", False)),
                    notice=str(d.get("notice") or state.get("notice") or ""),
                    support_url=str(d.get("support_url") or state.get("support_url") or DEFAULT_SUPPORT_URL),
                )
                _record_event("success", f"تم تفعيل الكود بنجاح ({res.message}).")
                _show_snack("تم تفعيل الترخيص بنجاح.")

                if bool(d.get("force_update", False)) and d.get("download_url"):
                    _on_download_click()
            else:
                save_state(
                    license_key=entered_key,
                    license_status=st_val,
                    license_message=res.message,
                )
                _record_event("error", f"فشل التحقق: {res.message}")
                _show_snack(res.message)
        finally:
            _set_busy(False)
            _refresh_ui()

    def _on_download_click() -> None:
        current = load_state()
        url = str(current.get("download_url") or "").strip()
        if not url:
            _show_snack("لا يوجد رابط حزمة متاح بعد؛ فعّل الكود أولاً.")
            return

        _set_busy(True)
        progress_bar.visible = True
        progress_label.visible = True
        progress_bar.value = 0.02
        progress_label.value = "بدء عملية التحميل..."
        try:
            page.update()
        except Exception:
            pass

        def progress_cb(frac: float, label: str) -> None:
            progress_bar.value = frac
            progress_label.value = label
            try:
                page.update()
            except Exception:
                pass

        try:
            inst_res = download_and_prepare(
                url,
                file_name=str(current.get("target_file_name") or DEFAULT_TARGET_FILE),
                expected_sha256=str(current.get("patch_sha256") or ""),
                deploy_mode=str(current.get("deploy_mode") or DEFAULT_DEPLOY_MODE),
                on_progress=progress_cb,
            )
            if inst_res.ok:
                save_state(
                    installed_patch_version=str(current.get("latest_patch_version") or "1"),
                    license_message=inst_res.message,
                )
                _record_event("success", inst_res.message)
                _show_snack("تم تحميل الحزمة وتجهيزها بنجاح.")
            else:
                _record_event("error", inst_res.message)
                _show_snack(inst_res.message)
        finally:
            progress_bar.visible = False
            progress_label.visible = False
            _set_busy(False)
            _refresh_ui()

    def _on_toggle_auto_update(e: ft.ControlEvent) -> None:
        val = bool(e.control.value)
        save_state(auto_update=val)
        _refresh_ui()

    def _on_toggle_notifications(e: ft.ControlEvent) -> None:
        val = bool(e.control.value)
        save_state(notifications_enabled=val)
        _refresh_ui()

    def _on_clear_logs(_: ft.ControlEvent) -> None:
        clear_logs()
        _refresh_ui()
        _show_snack("تم مسح السجل.")

    def _start_bg(fn) -> None:
        if is_busy:
            return
        threading.Thread(target=fn, daemon=True).start()

    home_view = ft.Column(
        controls=[
            notice_banner,
            update_alert_card,
            build_section_card(
                title="حالة الترخيص والاشتراك",
                subtitle=f"الهوية: {DEVELOPER_NAME} — {DEVELOPER_TAGLINE}",
                accent_color=COLOR_CYAN,
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[status_badge],
                            alignment=ft.MainAxisAlignment.START,
                        ),
                        status_message_txt,
                        ft.Row(
                            controls=[metric_days, metric_patch, metric_ota],
                            spacing=8,
                        ),
                        key_input,
                        ft.Row(
                            controls=[activate_btn, sync_btn],
                            spacing=10,
                            wrap=True,
                        ),
                    ],
                    spacing=12,
                ),
            ),
            build_section_card(
                title="إدارة الحزم والملفات",
                subtitle="تحميل آمن مع تحقق SHA-256 وفك ضغط تلقائي عند الحاجة",
                accent_color=COLOR_VIOLET,
                content=ft.Column(
                    controls=[
                        patch_info_txt,
                        progress_bar,
                        progress_label,
                        install_btn,
                    ],
                    spacing=10,
                ),
            ),
            build_section_card(
                title="ملاحظات التحديث عن بُعد (OTA)",
                subtitle="تحديثات النصوص والإعدادات دون إعادة تثبيت التطبيق",
                accent_color=COLOR_GREEN,
                content=ft.Column(
                    controls=[ota_notes_txt],
                    spacing=6,
                ),
            ),
        ],
        spacing=14,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    settings_view = ft.Column(
        controls=[
            build_section_card(
                title="تفضيلات التطبيق",
                subtitle="تحكم في المزامنة التلقائية وتسجيل الأحداث",
                accent_color=COLOR_CYAN,
                content=ft.Column(
                    controls=[
                        ft.Switch(
                            label="تحديث تلقائي عند التشغيل",
                            value=auto_update_switch.value,
                            active_color=COLOR_CYAN,
                            on_change=_on_toggle_auto_update,
                        ),
                        ft.Switch(
                            label="تسجيل التنبيهات في السجل",
                            value=notifications_switch.value,
                            active_color=COLOR_VIOLET,
                            on_change=_on_toggle_notifications,
                        ),
                    ],
                    spacing=8,
                ),
            ),
            build_section_card(
                title="معلومات الجهاز والتطبيق",
                subtitle="بيانات التعريف المحلية للتشخيص والدعم",
                accent_color=COLOR_VIOLET,
                content=ft.Column(
                    controls=[
                        device_id_txt,
                        app_ver_txt,
                        ft.ElevatedButton(
                            text="اختبار اتصال السيرفر الآن",
                            on_click=lambda _: _start_bg(
                                lambda: _show_snack(
                                    "السيرفر متصل وجاهز." if check_health().ok else "تعذر الوصول إلى السيرفر."
                                )
                            ),
                            style=ft.ButtonStyle(
                                bgcolor="#131D3F",
                                color=COLOR_CYAN,
                                shape=ft.RoundedRectangleBorder(radius=12),
                            ),
                        ),
                    ],
                    spacing=8,
                ),
            ),
        ],
        spacing=14,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    logs_view = ft.Column(
        controls=[
            ft.Row(
                controls=[
                    ft.Text("سجل العمليات والأحداث", size=16, weight=ft.FontWeight.BOLD, color=COLOR_TEXT),
                    ft.OutlinedButton(
                        text="مسح السجل",
                        on_click=_on_clear_logs,
                        style=ft.ButtonStyle(
                            color=COLOR_PINK,
                            side=ft.BorderSide(1, COLOR_PINK),
                            shape=ft.RoundedRectangleBorder(radius=10),
                        ),
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            logs_column,
        ],
        spacing=12,
        expand=True,
    )

    content_holder = ft.Container(
        content=home_view,
        padding=16,
        expand=True,
    )

    top_header = ft.Container(
        content=ft.Row(
            controls=[
                ft.Column(
                    controls=[
                        ft.Text(APP_TITLE, size=18, weight=ft.FontWeight.BOLD, color=COLOR_TEXT),
                        ft.Text(DEVELOPER_TAGLINE, size=11.5, color=COLOR_CYAN),
                    ],
                    spacing=1,
                ),
                ft.Container(
                    content=ft.Text(f"v{APP_VERSION}", size=12, weight=ft.FontWeight.BOLD, color=COLOR_CYAN),
                    padding=ft.padding.symmetric(horizontal=10, vertical=4),
                    border_radius=99,
                    bgcolor="#0E1836",
                    border=ft.border.all(1, "#223A78"),
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=16, vertical=12),
        bgcolor=COLOR_BG_ALT,
        border=ft.border.only(bottom=ft.BorderSide(1, "#19264E")),
    )

    def _switch_tab(idx: int) -> None:
        if idx == 0:
            content_holder.content = home_view
        elif idx == 1:
            content_holder.content = settings_view
        else:
            content_holder.content = logs_view
        _refresh_ui()

    nav_bar = ft.NavigationBar(
        bgcolor=COLOR_BG_ALT,
        indicator_color="#14234D",
        destinations=[
            ft.NavigationBarDestination(
                icon=getattr(ft.Icons, "VERIFIED_USER_OUTLINED", None) or getattr(ft.Icons, "HOME", None),
                label="الرئيسية",
            ),
            ft.NavigationBarDestination(
                icon=getattr(ft.Icons, "SETTINGS_OUTLINED", None) or getattr(ft.Icons, "SETTINGS", None),
                label="الإعدادات",
            ),
            ft.NavigationBarDestination(
                icon=getattr(ft.Icons, "HISTORY", None) or getattr(ft.Icons, "LIST", None),
                label="السجل",
            ),
        ],
        on_change=lambda e: _switch_tab(int(e.control.selected_index or 0)),
    )

    page.add(
        ft.Column(
            controls=[
                top_header,
                content_holder,
                nav_bar,
            ],
            spacing=0,
            expand=True,
        )
    )

    _refresh_ui()
    if state.get("auto_update", True):
        _start_bg(lambda: _sync_remote(manual=False))


if __name__ == "__main__":
    ft.app(target=main)
