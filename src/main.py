"""نقطة الدخول + الواجهة."""
from __future__ import annotations

import asyncio
import re
from typing import Optional

import flet as ft

import api
import installer
import state
from config import CFG

# ---------------------------------------------------------------- الألوان (نفس هوية لوحة التحكم)
INK = "#0F1411"
PLATE = "#161D18"
PLATE2 = "#1F2922"
RULE = "#2A352D"
TEXT = "#E9EEE6"
MUT = "#8E9C91"
SAND = "#D8BF8A"
SAND_INK = "#241C0A"
MOSS = "#86AD6F"
RUST = "#E0803F"
CRIM = "#E0606A"


def _icon(name: str, fallback=None):
    """أيقونة آمنة: إن لم يوجد الاسم في نسخة Flet المثبّتة نستخدم بديلاً بدل أن ينهار التطبيق."""
    return getattr(ft.Icons, name, fallback or ft.Icons.INFO)


def _vt(v: str) -> tuple:
    return tuple(int(x) for x in re.findall(r"\d+", v or "")[:4]) or (0,)


def make_button(text: str, icon=None, on_click=None, kind: str = "primary", **kw) -> ft.Button:
    colors = {
        "primary": (SAND, SAND_INK),
        "secondary": (PLATE2, TEXT),
        "danger": ("#3A1D21", CRIM),
        "ghost": (ft.Colors.TRANSPARENT, MUT),
    }
    bg, fg = colors[kind]
    return ft.Button(
        content=text, icon=icon, on_click=on_click, bgcolor=bg, color=fg, height=50,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)), **kw,
    )


def card(content: ft.Control, **kw) -> ft.Container:
    return ft.Container(
        content=content, padding=18, border_radius=16, bgcolor=PLATE,
        border=ft.Border.all(1, RULE), **kw,
    )


def kv_row(label: str, value: ft.Control) -> ft.Row:
    return ft.Row(
        [ft.Text(label, size=13.5, color=MUT), value],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )


class App:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.busy = False
        self._clip = None
        self._arm_task: Optional[asyncio.Task] = None
        self._last_pct = -1
        self._staged = None
        self._manual_kind = "install"
        self.license: Optional[api.LicenseResult] = None
        self.installed_version: str = state.load().get("installed_version", "")
        self.support_url = ""
        self.cfg_notice = ""

        # ---------- الرأس ----------
        self.header = ft.Row(
            [
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Icon(_icon("VERIFIED_USER"), size=24, color=SAND),
                            width=46, height=46, border_radius=12, alignment=ft.Alignment.CENTER,
                            bgcolor=ft.Colors.with_opacity(0.12, SAND),
                        ),
                        ft.Column(
                            [
                                ft.Text(CFG.APP_TITLE, size=18, weight=ft.FontWeight.BOLD, color=TEXT),
                                ft.Text("إدارة الاشتراك والباتش", size=12.5, color=MUT),
                            ],
                            spacing=0,
                        ),
                    ],
                    spacing=12,
                ),
                ft.Text(f"v{CFG.APP_VERSION}", size=12, color=MUT),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        # ---------- إعلان من المشرف ----------
        self.banner_text = ft.Text("", size=13.5, color=TEXT, expand=True)
        self.banner = ft.Container(
            visible=False, padding=14, border_radius=12,
            bgcolor=ft.Colors.with_opacity(0.10, SAND),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.35, SAND)),
            content=ft.Row([ft.Icon(_icon("CAMPAIGN"), size=20, color=SAND), self.banner_text], spacing=10),
        )

        # ---------- شاشة طلب تحديث التطبيق ----------
        self.update_msg = ft.Text("", size=14, color=TEXT, text_align=ft.TextAlign.CENTER)
        self.update_btn = make_button("تحميل النسخة الجديدة", _icon("SYSTEM_UPDATE"), url="https://example.com", visible=False)
        self.update_panel = card(
            ft.Column(
                [ft.Icon(_icon("SYSTEM_UPDATE"), size=42, color=SAND),
                 ft.Text("تحديث مطلوب", size=18, weight=ft.FontWeight.BOLD, color=TEXT),
                 self.update_msg, self.update_btn],
                spacing=12, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            visible=False,
        )

        # ---------- بطاقة التفعيل ----------
        self.key_input = ft.TextField(
            label="كود التفعيل", password=True, can_reveal_password=True,
            text_align=ft.TextAlign.CENTER, on_submit=self.on_activate,
            border_radius=12, border_color=RULE, focused_border_color=SAND,
        )
        self.activate_btn = make_button("تحقق وفعّل", _icon("SECURITY"), self.on_activate)
        self.activation_card = card(
            ft.Column(
                [
                    ft.Text("تفعيل الاشتراك", size=17, weight=ft.FontWeight.BOLD, color=TEXT),
                    ft.Text("أدخل الكود الذي استلمته، وسيُحمَّل الباتش ويُثبَّت تلقائياً.", size=13, color=MUT),
                    ft.Container(height=2),
                    self.key_input,
                    self.activate_btn,
                ],
                spacing=10, horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            )
        )

        # ---------- بطاقة الحساب (بعد التفعيل) ----------
        self.days_text = ft.Text("0", size=46, weight=ft.FontWeight.BOLD, color=SAND)
        self.days_label = ft.Text("يوم متبقٍ", size=14, color=MUT)
        self.meter = ft.ProgressBar(value=1, color=MOSS, bgcolor=RULE)
        self.expiry_text = ft.Text("", size=12.5, color=MUT)
        self.installed_text = ft.Text("غير مثبّت", size=14, weight=ft.FontWeight.W_600, color=TEXT)
        self.latest_text = ft.Text("—", size=14, weight=ft.FontWeight.W_600, color=TEXT)
        self.update_badge = ft.Container(
            content=ft.Text("تحديث متاح", size=12, weight=ft.FontWeight.BOLD, color=SAND_INK),
            bgcolor=SAND, padding=5, border_radius=99, visible=False,
        )
        self.install_btn = make_button("تثبيت الباتش", _icon("DOWNLOAD"), self.on_install)
        self.remove_btn = make_button("حذف الباتش", _icon("DELETE"), self.on_remove_click, kind="secondary")
        self.logout_btn = make_button("تغيير الكود", _icon("LOGOUT"), self.on_logout, kind="ghost")
        self.account_card = card(
            ft.Column(
                [
                    ft.Row(
                        [ft.Text("اشتراكك", size=17, weight=ft.FontWeight.BOLD, color=TEXT),
                         ft.Container(
                             content=ft.Text("نشط", size=12, weight=ft.FontWeight.BOLD, color=MOSS),
                             padding=5, border_radius=99, border=ft.Border.all(1, MOSS))],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Row([self.days_text, self.days_label], spacing=8,
                           vertical_alignment=ft.CrossAxisAlignment.END),
                    self.meter,
                    self.expiry_text,
                    ft.Container(height=1, bgcolor=RULE, margin=4),
                    kv_row("الباتش المثبّت", ft.Row([self.update_badge, self.installed_text], spacing=8)),
                    kv_row("أحدث إصدار", self.latest_text),
                    ft.Container(height=4),
                    self.install_btn,
                    self.remove_btn,
                    self.logout_btn,
                ],
                spacing=10, horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
            visible=False,
        )

        # ---------- حالة العملية ----------
        self.status = ft.Text("", size=14, color=MUT, text_align=ft.TextAlign.CENTER)
        self.progress = ft.ProgressBar(visible=False, color=SAND, bgcolor=RULE)

        # ---------- لوحة النقل اليدوي ----------
        self.manual_title = ft.Text("", size=15, weight=ft.FontWeight.BOLD, color=SAND)
        self.manual_steps = ft.Text("", size=13, color=TEXT)
        self.cmd_field = ft.TextField(
            value="", read_only=True, multiline=True, min_lines=3, max_lines=6, text_size=12,
            border_radius=10, border_color=RULE,
        )
        self.diag = ft.Text("", size=11.5, color=MUT, selectable=True)
        self.copy_btn = make_button("نسخ الأمر", _icon("COPY"), self.on_copy, kind="secondary")
        self.done_btn = make_button("تم التنفيذ", _icon("CHECK_CIRCLE"), self.on_manual_done)
        self.manual_panel = ft.Container(
            visible=False, padding=16, border_radius=14,
            bgcolor=ft.Colors.with_opacity(0.07, SAND),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.30, SAND)),
            content=ft.Column(
                [self.manual_title, self.manual_steps, self.cmd_field, self.copy_btn, self.done_btn, self.diag],
                spacing=10, horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
        )

        # ---------- التذييل ----------
        self.support_btn = make_button("متابعة آخر التحديثات", _icon("SUPPORT_AGENT"), kind="secondary",
                                       url="https://example.com", visible=False)

    # =============================================================== مساعدات الواجهة
    def set_status(self, msg: str, color=MUT) -> None:
        self.status.value = msg
        self.status.color = color
        self.page.update()

    def set_busy(self, busy: bool) -> None:
        self.busy = busy
        for c in (self.activate_btn, self.install_btn, self.remove_btn, self.logout_btn, self.key_input):
            c.disabled = busy
        self.progress.visible = busy
        if busy:
            self.progress.value = None
            self._last_pct = -1
        self.page.update()

    def on_progress(self, value: Optional[float]) -> None:
        if value is not None:
            pct = int(value * 100)
            if pct == self._last_pct:
                return
            self._last_pct = pct
            self.status.value = f"جاري تحميل الباتش… {pct}%"
            self.status.color = SAND
        self.progress.value = value
        self.page.update()

    def show_banner(self, text: str) -> None:
        self.banner_text.value = text
        self.banner.visible = bool(text)
        self.page.update()

    def apply_support(self, url: str) -> None:
        if url:
            self.support_url = url
        self.support_btn.url = self.support_url or "https://example.com"
        self.support_btn.visible = bool(self.support_url)

    def show_update_required(self, message: str, url: str) -> None:
        self.activation_card.visible = False
        self.account_card.visible = False
        self.update_msg.value = message or "يجب تحديث التطبيق للمتابعة."
        self.update_btn.visible = bool(url)
        if url:
            self.update_btn.url = url
        self.update_panel.visible = True
        self.page.update()

    def show_account(self) -> None:
        self.activation_card.visible = False
        self.account_card.visible = True
        self.refresh_account()

    def show_activation(self) -> None:
        self.account_card.visible = False
        self.activation_card.visible = True
        self.page.update()

    def needs_update(self) -> bool:
        lic = self.license
        return bool(lic and lic.patch_version and self.installed_version
                    and lic.patch_version != self.installed_version)

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
        self.meter.color = SAND if soon else MOSS
        self.days_text.color = RUST if lic.remaining_days <= 1 else SAND
        self.expiry_text.value = f"ينتهي في {lic.expires_at[:10]}" if lic.expires_at else ""
        self.installed_text.value = f"رقم {self.installed_version}" if self.installed_version else "غير مثبّت"
        self.latest_text.value = f"رقم {lic.patch_version}" if lic.patch_version else "—"
        outdated = self.needs_update()
        self.update_badge.visible = outdated
        if outdated:
            self.install_btn.content = "تحديث الباتش"
        elif self.installed_version:
            self.install_btn.content = "إعادة تثبيت الباتش"
        else:
            self.install_btn.content = "تثبيت الباتش"
        self.page.update()

    def mark_installed(self, version: str) -> None:
        self.installed_version = version or ""
        state.save(installed_version=version or None)
        self.refresh_account()

    # ---------- النقل اليدوي ----------
    def show_manual(self, command: str, kind: str) -> None:
        self._manual_kind = kind
        self.cmd_field.value = command
        if kind == "remove":
            self.manual_title.value = "حذف الباتش يدوياً"
            self.manual_steps.value = (
                "١) افتح طرفية تعمل بـ Shizuku (مثل aShell You)\n"
                "٢) الصق الأمر التالي ونفّذه\n"
                "٣) ارجع هنا واضغط «تم التنفيذ»"
            )
        else:
            self.manual_title.value = "الملف جاهز، أكمل التثبيت"
            self.manual_steps.value = (
                "١) افتح طرفية تعمل بـ Shizuku (مثل aShell You)\n"
                "٢) الصق الأمر التالي ونفّذه\n"
                "٣) تأكد أن آخر سطر يعرض اسم الملف وحجمه، ثم اضغط «تم التنفيذ»"
            )
        st = installer.last_staging
        if kind == "remove" or st is None:
            self.diag.value = ""
        elif st.shell_readable:
            self.diag.value = f"📁 مكان الملف: {st.path}"
            self.diag.color = MUT
        else:
            self.diag.value = (
                "⚠️ تعذر حفظ الملف في مكان يقرؤه Shizuku، لذلك الأمر لن ينجح.\n"
                "فعّل: الإعدادات ← التطبيقات ← PUBG VIP Manager ← الأذونات ← الملفات ← السماح بإدارة كل الملفات، ثم أعد المحاولة.\n"
                + "\n".join(st.notes)
            )
            self.diag.color = CRIM
        self.manual_panel.visible = True
        self.page.update()

    def hide_manual(self) -> None:
        self.manual_panel.visible = False
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
            MOSS if ok else RUST,
        )

    async def on_manual_done(self, e) -> None:
        if self._manual_kind == "remove":
            self.mark_installed("")
            self.set_status("تم حذف الباتش ✅", MOSS)
        else:
            self.mark_installed(self.license.patch_version if self.license else "")
            installer.cleanup(self._staged)
            self._staged = None
            self.set_status("تم تثبيت الباتش ✅ افتح اللعبة الآن.", MOSS)
        self.hide_manual()

    # =============================================================== العمليات
    async def start(self) -> None:
        cfg = await api.fetch_app_config()
        self.apply_support(cfg.get("support_url") or "")
        self.cfg_notice = cfg.get("notice") or ""
        self.show_banner(self.cfg_notice)

        min_ver = cfg.get("min_app_version") or ""
        if min_ver and _vt(CFG.APP_VERSION) < _vt(min_ver):
            self.show_update_required("يجب تحديث التطبيق للمتابعة.", cfg.get("update_url") or "")
            return

        saved = state.load().get("key") or ""
        if not saved:
            self.page.update()
            return
        self.key_input.value = saved
        self.set_busy(True)
        try:
            self.set_status("جاري التحقق من اشتراكك…", SAND)
            ok = await self.verify(saved, auto=True)
            if ok and self.license and self.license.force_update and self.needs_update():
                self.set_status("يوجد تحديث إلزامي للباتش، جاري التثبيت…", SAND)
                await self.do_install()
        finally:
            self.set_busy(False)

    async def verify(self, key: str, auto: bool = False) -> bool:
        """يتحقق من الكود ويحدّث الواجهة. لا يغيّر حالة 'busy' (المستدعي يتولاها)."""
        result = await api.verify_license(key)
        S = api.LicenseStatus
        if result.status is S.ACTIVE:
            self.license = result
            state.save(key=key)
            if result.notice:
                self.show_banner(result.notice)
            self.apply_support(result.support_url)
            self.show_account()
            self.set_status("", MUT)
            return True
        if result.status is S.UPDATE_REQUIRED:
            self.show_update_required(result.message, result.update_url)
            return False
        if result.status is S.MAINTENANCE:
            self.show_banner(result.message)
        if result.status is S.INVALID:
            state.save(key=None)
        self.show_activation()
        color = RUST if result.status in (S.NETWORK_ERROR, S.MAINTENANCE, S.SERVER_ERROR) else CRIM
        self.set_status(("" if auto and result.status is S.NETWORK_ERROR else "❌ ") + result.message, color)
        return False

    async def on_activate(self, e) -> None:
        if self.busy:
            return
        key = (self.key_input.value or "").strip()
        if not key:
            self.set_status("الرجاء كتابة الكود أولاً!", CRIM)
            return
        self.set_busy(True)
        try:
            self.set_status("جاري التحقق من الكود…", SAND)
            if await self.verify(key) and not self.installed_version:
                self.set_status("الكود صالح! جاري تحميل الباتش…", SAND)
                await self.do_install()
        except Exception as ex:  # noqa: BLE001
            self.set_status(f"حدث خطأ غير متوقع: {ex}", CRIM)
        finally:
            self.set_busy(False)

    async def on_install(self, e) -> None:
        if self.busy or self.license is None:
            return
        self.set_busy(True)
        try:
            # نعيد التحقق أولاً للحصول على آخر رابط/رقم باتش وللتأكد أن الاشتراك ما زال فعّالاً
            key = state.load().get("key") or (self.key_input.value or "").strip()
            if key and not await self.verify(key):
                return
            await self.do_install()
        except Exception as ex:  # noqa: BLE001
            self.set_status(f"حدث خطأ غير متوقع: {ex}", CRIM)
        finally:
            self.set_busy(False)

    async def do_install(self) -> None:
        lic = self.license
        if lic is None:
            return
        if not (lic.download_url or CFG.PATCH_DOWNLOAD_URL or CFG.PATCH_MIRRORS):
            self.set_status("لم يضف المشرف رابط الباتش بعد. تواصل مع الدعم.", RUST)
            return
        self.hide_manual()
        installer.configure_target(lic.target_file_name, lic.game_package)
        staged = None
        keep_file = False
        try:
            self.set_status("جاري تحميل الباتش…", SAND)
            staged = await installer.download_patch(self.on_progress, lic.download_url)
            self.progress.value = None
            self.set_status("تم التحميل! جاري التثبيت…", SAND)
            res = await installer.install_patch(staged)
            self.mark_installed(lic.patch_version)
            how = "عبر Shizuku" if res.method == "shizuku" else "مباشرة"
            self.set_status(f"تم تثبيت الباتش {how} ✅ افتح اللعبة الآن.", MOSS)
        except installer.InstallError as ex:
            if ex.manual_command:
                keep_file = True  # نحتفظ بالملف ليستخدمه الأمر اليدوي
                self._staged = staged
                self.set_status(f"⚠️ {ex}", RUST)
                self.show_manual(ex.manual_command, "install")
            else:
                self.set_status(f"❌ {ex}", CRIM)
        finally:
            if not keep_file:
                installer.cleanup(staged)

    # ---------- حذف الباتش (ضغطتان للتأكيد) ----------
    def _disarm(self) -> None:
        if self._arm_task and not self._arm_task.done():
            self._arm_task.cancel()
        self._arm_task = None
        self.remove_btn.content = "حذف الباتش"
        self.remove_btn.bgcolor = PLATE2
        self.remove_btn.color = TEXT

    async def _disarm_later(self) -> None:
        try:
            await asyncio.sleep(4)
        except asyncio.CancelledError:
            return
        self._arm_task = None
        self._disarm()
        self.page.update()

    async def on_remove_click(self, e) -> None:
        if self.busy:
            return
        if self._arm_task is None:
            self.remove_btn.content = "اضغط مرة أخرى لتأكيد الحذف"
            self.remove_btn.bgcolor = "#3A1D21"
            self.remove_btn.color = CRIM
            self._arm_task = asyncio.create_task(self._disarm_later())
            self.page.update()
            return
        self._disarm()
        self.set_busy(True)
        try:
            await self.do_remove()
        finally:
            self.set_busy(False)

    async def do_remove(self) -> None:
        lic = self.license
        installer.configure_target(lic.target_file_name if lic else "", lic.game_package if lic else "")
        self.hide_manual()
        try:
            self.set_status("جاري حذف الباتش…", SAND)
            res = await installer.remove_patch()
            self.mark_installed("")
            how = "عبر Shizuku" if res.method == "shizuku" else "مباشرة"
            self.set_status(f"تم حذف الباتش {how} ✅", MOSS)
        except installer.InstallError as ex:
            self.set_status(f"⚠️ {ex}", RUST)
            self.show_manual(ex.manual_command, "remove")
        except Exception as ex:  # noqa: BLE001
            self.set_status(f"حدث خطأ غير متوقع: {ex}", CRIM)

    async def on_logout(self, e) -> None:
        if self.busy:
            return
        state.save(key=None)
        self.license = None
        self.key_input.value = ""
        self.hide_manual()
        self.set_status("", MUT)
        self.show_activation()

    # =============================================================== البناء
    def build(self) -> ft.Control:
        content = ft.Column(
            [
                self.header,
                self.banner,
                self.update_panel,
                self.activation_card,
                self.account_card,
                ft.Column([self.progress, self.status], spacing=8,
                          horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
                self.manual_panel,
                self.support_btn,
            ],
            spacing=14, scroll=ft.ScrollMode.AUTO, horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            expand=True,
        )
        return ft.SafeArea(content=ft.Container(content=content, padding=16, expand=True), expand=True)


async def main(page: ft.Page) -> None:
    page.title = CFG.APP_TITLE
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = ft.Theme(color_scheme_seed=SAND)
    page.bgcolor = INK
    page.padding = 0
    try:  # اتجاه عربي (من اليمين لليسار) إن كانت نسخة Flet تدعمه
        page.locale_configuration = ft.LocaleConfiguration(
            supported_locales=[ft.Locale("ar"), ft.Locale("en")], current_locale=ft.Locale("ar"),
        )
    except Exception:  # noqa: BLE001
        pass
    view = App(page)
    page.add(view.build())
    await view.start()


if __name__ == "__main__":
    ft.run(main)
