import asyncio
import os
import shutil
import tempfile

import flet as ft
import httpx

# =====================================================================
# 🛠️ [منطقة إعدادات المطور] - يمكنك تعديل أي رابط أو اسم بسهولة تامة هنا
# =====================================================================
class Config:
    # رابط سيرفر التحقق المركزي (Vercel)
    SERVER_URL = "https://pak-license-server.vercel.app"

    # رابط تحميل ملف الباتش المباشر (Catbox)
    PATCH_DOWNLOAD_URL = "https://files.catbox.moe/nwnc4y.pak"

    # الاسم النهائي والدقيق لملف الباتش داخل ملفات اللعبة
    TARGET_FILE_NAME = "res_pufferpatch_4.6.1.21589.pak"

    # مسار حفظ الباتش الرسمي داخل لعبة ببجي
    TARGET_DIR = "/storage/emulated/0/Android/data/com.tencent.ig/files/UE4Game/ShadowTrackerExtra/ShadowTrackerExtra/Saved/Paks/"
# =====================================================================


async def main(page: ft.Page):
    page.title = "PUBG VIP Manager Pro"
    page.theme_mode = ft.ThemeMode.DARK
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    # واجهة إدخال كود التفعيل
    key_input = ft.TextField(
        label="أدخل كود التفعيل VIP",
        password=True,
        can_reveal_password=True,
        width=320,
    )

    status_text = ft.Text(
        "أدخل الكود للاتصال بالسيرفر...",
        size=14,
        color=ft.Colors.WHITE_70,
        text_align=ft.TextAlign.CENTER,
    )
    progress_bar = ft.ProgressBar(width=320, visible=False, color=ft.Colors.AMBER)

    async def set_status(msg: str, color) -> None:
        status_text.value = msg
        status_text.color = color
        status_text.update()

    async def process_activation(e) -> None:
        key = key_input.value.strip()
        if not key:
            await set_status("الرجاء كتابة الكود أولاً!", ft.Colors.RED)
            return

        action_btn.disabled = True
        action_btn.update()
        progress_bar.visible = True
        progress_bar.value = None  # وضع التحميل غير المحدد أثناء التحقق
        progress_bar.update()
        await set_status("جاري الاتصال بالسيرفر المركزي...", ft.Colors.BLUE_400)

        temp_file_path = None
        try:
            # 1. الاتصال بسيرفر Vercel للتحقق من صلاحية الكود (async - لا يجمّد الواجهة)
            async with httpx.AsyncClient(timeout=20) as client:
                res = await client.post(
                    f"{Config.SERVER_URL}/api/verify",
                    json={"key": key, "device_id": "android_device_01"},
                )
            res_data = res.json()
            status = res_data.get("status")

            if status == "active":
                await set_status("الكود صالح! جاري تحميل ملف الباتش...", ft.Colors.BLUE_400)

                # 2. تحميل ملف الباتش مع شريط تقدم حقيقي (نسبة مئوية)
                temp_file_path = os.path.join(tempfile.gettempdir(), Config.TARGET_FILE_NAME)
                async with httpx.AsyncClient(timeout=300) as client:
                    async with client.stream("GET", Config.PATCH_DOWNLOAD_URL) as r:
                        r.raise_for_status()
                        total = int(r.headers.get("content-length", 0))
                        downloaded = 0
                        with open(temp_file_path, "wb") as f:
                            async for chunk in r.aiter_bytes(65536):
                                f.write(chunk)
                                downloaded += len(chunk)
                                if total:
                                    progress_bar.value = downloaded / total
                                    progress_bar.update()

                await set_status("تم التحميل! جاري الحقن بالاسم الصحيح...", ft.Colors.BLUE_400)

                # 3. الحقن عبر Shizuku (rish) ثم المحاولة المباشرة كبديل
                injected = False
                try:
                    cmd = f"cp '{temp_file_path}' '{Config.TARGET_DIR}{Config.TARGET_FILE_NAME}'"
                    proc = await asyncio.create_subprocess_exec(
                        "rish", "-c", cmd,
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL,
                    )
                    await proc.wait()
                    injected = proc.returncode == 0
                except Exception:
                    injected = False

                if not injected:
                    try:
                        os.makedirs(Config.TARGET_DIR, exist_ok=True)
                        shutil.copy(temp_file_path, os.path.join(Config.TARGET_DIR, Config.TARGET_FILE_NAME))
                        injected = True
                    except Exception:
                        injected = False

                if injected:
                    await set_status("تم حقن الباتش وتفعيله بنجاح تام! ✅", ft.Colors.GREEN_400)
                else:
                    await set_status("فشل النقل! تأكد من تفعيل صلاحيات Shizuku على جهازك.", ft.Colors.RED_400)

            elif status == "banned":
                await set_status("عذراً، هذا الكود محظور نهائياً (Banned) ❌", ft.Colors.RED_400)
            else:
                await set_status(res_data.get("message", "الكود غير صالح أو منتهي!"), ft.Colors.RED_400)

        except httpx.ConnectError:
            await set_status("تعذر الاتصال بالسيرفر، تأكد من اتصال الإنترنت.", ft.Colors.RED_400)
        except Exception as ex:
            await set_status(f"حدث خطأ غير متوقع: {ex}", ft.Colors.RED_400)
        finally:
            progress_bar.visible = False
            progress_bar.update()
            action_btn.disabled = False
            action_btn.update()
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except OSError:
                    pass

    action_btn = ft.Button(
        content="تحقق وفعل الباتش",
        icon=ft.Icons.SECURITY,
        on_click=process_activation,
        bgcolor=ft.Colors.RED_900,
        color=ft.Colors.WHITE,
        width=320,
    )

    page.add(
        ft.Container(
            content=ft.Column(
                [
                    ft.Text("PUBG VIP Control Panel", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_ACCENT),
                    ft.Divider(height=25, color=ft.Colors.TRANSPARENT),
                    key_input,
                    ft.Divider(height=15, color=ft.Colors.TRANSPARENT),
                    action_btn,
                    ft.Divider(height=25, color=ft.Colors.TRANSPARENT),
                    progress_bar,
                    ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                    status_text,
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=20,
            alignment=ft.Alignment.CENTER,
        )
    )


# نقطة الدخول الرسمية في Flet 1.0 (استبدل ft.app القديمة)
if __name__ == "__main__":
    ft.run(main)
