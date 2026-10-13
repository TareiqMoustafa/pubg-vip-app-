"""نقطة الدخول + الواجهة."""
from __future__ import annotations

from typing import Optional

import flet as ft

import api
import installer
from config import CFG


class ActivationView:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.busy = False
        self._clip = None

        self.key_input = ft.TextField(
            label="أدخل كود التفعيل VIP",
            password=True,
            can_reveal_password=True,
            width=320,
            text_align=ft.TextAlign.CENTER,
            on_submit=self.on_activate,
        )
        self.status = ft.Text(
            "أدخل الكود للاتصال بالسيرفر...",
            size=14,
            color=ft.Colors.WHITE_70,
            text_align=ft.TextAlign.CENTER,
        )
        self.progress = ft.ProgressBar(width=320, visible=False, color=ft.Colors.AMBER)
        self.button = ft.Button(
            content="تحقق وفعل الباتش",
            icon=ft.Icons.SECURITY,
            on_click=self.on_activate,
            bgcolor=ft.Colors.RED_900,
            color=ft.Colors.WHITE,
            width=320,
        )

        # لوحة النقل اليدوي (تظهر فقط إذا تعذر النقل التلقائي)
        self.cmd_field = ft.TextField(
            value="", read_only=True, multiline=True, min_lines=3, max_lines=6,
            text_size=12, width=300,
        )
        self.diag = ft.Text("", size=11, color=ft.Colors.WHITE_54, selectable=True)
        self.copy_btn = ft.Button(
            content="نسخ الأمر", icon=ft.Icons.COPY, on_click=self.on_copy,
            bgcolor=ft.Colors.AMBER_700, color=ft.Colors.BLACK, width=300,
        )
        self.manual_panel = ft.Container(
            visible=False,
            padding=14,
            border_radius=14,
            bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.AMBER),
            content=ft.Column(
                [
                    ft.Text(
                        "الملف جاهز. لإكمال التثبيت:\n"
                        "١) افتح طرفية تعمل بـ Shizuku (مثل aShell You)\n"
                        "٢) الصق الأمر التالي ونفّذه\n"
                        "٣) تأكد أن آخر سطر يعرض اسم الملف وحجمه، ثم افتح اللعبة",
                        size=13, text_align=ft.TextAlign.START,
                    ),
                    self.cmd_field,
                    self.copy_btn,
                    self.diag,
                ],
                spacing=10,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    # ---------- مساعدات الواجهة ----------
    def set_status(self, msg: str, color) -> None:
        self.status.value = msg
        self.status.color = color
        self.status.update()

    def set_progress(self, value: Optional[float]) -> None:
        self.progress.value = value
        self.progress.update()

    def set_busy(self, busy: bool) -> None:
        self.busy = busy
        self.button.disabled = busy
        self.key_input.disabled = busy
        self.progress.visible = busy
        if busy:
            self.progress.value = None
            self.manual_panel.visible = False
        self.page.update()

    def show_manual(self, command: str) -> None:
        self.cmd_field.value = command
        st = installer.last_staging
        if st is None:
            self.diag.value = ""
        elif st.shell_readable:
            self.diag.value = f"📁 مكان الملف: {st.path}"
            self.diag.color = ft.Colors.WHITE_54
        else:
            self.diag.value = (
                "⚠️ تعذر حفظ الملف في مكان يقرؤه Shizuku، لذلك الأمر لن ينجح.\n"
                "فعّل: الإعدادات ← التطبيقات ← PUBG VIP Manager ← الأذونات ← الملفات ← السماح بإدارة كل الملفات، ثم أعد المحاولة.\n"
                + "\n".join(st.notes)
            )
            self.diag.color = ft.Colors.RED_300
        self.manual_panel.visible = True
        self.page.update()

    async def on_copy(self, e) -> None:
        text = self.cmd_field.value or ""
        ok = False
        try:
            if self._clip is None:
                self._clip = ft.Clipboard()
                self.page.services.append(self._clip)
            await self._clip.set(text)
            ok = True
        except Exception:
            try:
                self.page.set_clipboard(text)
                ok = True
            except Exception:
                ok = False
        self.set_status(
            "تم نسخ الأمر ✅" if ok else "تعذر النسخ التلقائي: اضغط مطولاً على الأمر وانسخه يدوياً.",
            ft.Colors.GREEN_400 if ok else ft.Colors.AMBER_400,
        )

    # ---------- العملية الرئيسية ----------
    async def on_activate(self, e) -> None:
        if self.busy:
            return
        key = (self.key_input.value or "").strip()
        if not key:
            self.set_status("الرجاء كتابة الكود أولاً!", ft.Colors.RED_400)
            return

        self.set_busy(True)
        staged = None
        keep_file = False
        try:
            self.set_status("جاري التحقق من الكود...", ft.Colors.BLUE_400)
            result = await api.verify_license(key)
            if result.status is not api.LicenseStatus.ACTIVE:
                self.set_status(f"❌ {result.message}", ft.Colors.RED_400)
                return

            self.set_status("الكود صالح! جاري تحميل الباتش...", ft.Colors.BLUE_400)
            installer.configure_target(result.target_file_name, result.game_package)
            staged = await installer.download_patch(self.set_progress, result.download_url)

            self.set_progress(None)
            self.set_status("تم التحميل! جاري التثبيت...", ft.Colors.BLUE_400)
            res = await installer.install_patch(staged)

            how = "عبر Shizuku" if res.method == "shizuku" else "مباشرة"
            self.set_status(f"تم تثبيت الباتش بنجاح {how} ✅", ft.Colors.GREEN_400)
        except installer.InstallError as ex:
            if ex.manual_command:
                keep_file = True  # نحتفظ بالملف ليستخدمه الأمر اليدوي
                self.set_status(f"⚠️ {ex}", ft.Colors.AMBER_400)
                self.show_manual(ex.manual_command)
            else:
                self.set_status(f"❌ {ex}", ft.Colors.RED_400)
        except Exception as ex:
            self.set_status(f"حدث خطأ غير متوقع: {ex}", ft.Colors.RED_400)
        finally:
            if not keep_file:
                installer.cleanup(staged)
            self.set_busy(False)
            if keep_file:
                self.manual_panel.visible = True
                self.page.update()

    # ---------- البناء ----------
    def build(self) -> ft.Control:
        card = ft.Container(
            padding=24,
            border_radius=20,
            bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.WHITE),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.12, ft.Colors.WHITE)),
            content=ft.Column(
                [
                    ft.Icon(ft.Icons.VERIFIED_USER, size=48, color=ft.Colors.AMBER_ACCENT),
                    ft.Text("PUBG VIP Control Panel", size=20, weight=ft.FontWeight.BOLD,
                            color=ft.Colors.AMBER_ACCENT),
                    ft.Container(height=10),
                    self.key_input,
                    self.button,
                    ft.Container(height=6),
                    self.progress,
                    self.status,
                    self.manual_panel,
                ],
                spacing=12,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                scroll=ft.ScrollMode.AUTO,
            ),
        )
        return ft.SafeArea(
            content=ft.Container(content=card, alignment=ft.Alignment.CENTER, expand=True, padding=16),
            expand=True,
        )


async def main(page: ft.Page) -> None:
    page.title = CFG.APP_TITLE
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.RED)
    page.padding = 0
    page.add(ActivationView(page).build())


if __name__ == "__main__":
    ft.run(main)
