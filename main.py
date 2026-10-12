import flet as ft
import requests
import os
import threading
import tempfile
import subprocess

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

def main(page: ft.Page):
    page.title = "PUBG VIP Manager Pro"
    page.theme_mode = ft.ThemeMode.DARK
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.window_width = 400
    page.window_height = 650

    # واجهة إدخال كود التفعيل
    key_input = ft.TextField(
        label="أدخل كود التفعيل VIP",
        password=True,
        can_reveal_password=True,
        border_color=ft.colors.AMBER,
        focused_border_color=ft.colors.GREEN,
        width=320
    )
    
    status_text = ft.Text("أدخل الكود للاتصال بالسيرفر...", size=14, color=ft.colors.WHITE70, text_align=ft.TextAlign.CENTER)
    progress_bar = ft.ProgressBar(width=320, visible=False, color=ft.colors.AMBER)

    def process_activation(e):
        key = key_input.value.strip()
        if not key:
            status_text.value = "الرجاء كتابة الكود أولاً!"
            status_text.color = ft.colors.RED
            page.update()
            return

        status_text.value = "جاري الاتصال بالسيرفر المركزي..."
        status_text.color = ft.colors.BLUE_400
        progress_bar.visible = True
        action_btn.disabled = True
        page.update()

        def background_task():
            try:
                # 1. الاتصال بسيرفر Vercel للتحقق من صلاحية الكود
                res = requests.post(f"{Config.SERVER_URL}/api/verify", json={"key": key, "device_id": "android_device_01"}, timeout=10)
                res_data = res.json()
                status = res_data.get("status")

                if status == "active":
                    status_text.value = "الكود صالح! جاري تحميل ملف الباتش..."
                    page.update()

                    # 2. تحميل ملف الباتش من الرابط المحدد في الإعدادات
                    patch_res = requests.get(Config.PATCH_DOWNLOAD_URL, stream=True, timeout=25)
                    
                    if patch_res.status_code == 200:
                        temp_dir = tempfile.gettempdir()
                        temp_file_path = os.path.join(temp_dir, Config.TARGET_FILE_NAME)
                        
                        # كتابة الملف مؤقتاً في ذاكرة الهاتف أثناء التحميل
                        with open(temp_file_path, "wb") as f:
                            for chunk in patch_res.iter_content(chunk_size=1024):
                                if chunk:
                                    f.write(chunk)

                        status_text.value = "تم التحميل! جاري الحقن بالاسم الصحيح..."
                        page.update()

                        # 3. نقل الملف وتفعيله عبر Shizuku (أمر rish) لتجاوز قيود أندرويد الحديثة
                        cmd = f"cp '{temp_file_path}' '{Config.TARGET_DIR}{Config.TARGET_FILE_NAME}'"
                        process = subprocess.run(['rish', '-c', cmd], capture_output=True, text=True)

                        if process.returncode == 0:
                            status_text.value = "تم حقن الباتش وتفعيله بنجاح تام عبر Shizuku! ✅"
                            status_text.color = ft.colors.GREEN_400
                        else:
                            # محاولة النقل بالطريقة العادية لو الجهاز يمتلك صلاحيات مباشرة
                            try:
                                os.makedirs(Config.TARGET_DIR, exist_ok=True)
                                import shutil
                                shutil.copy(temp_file_path, os.path.join(Config.TARGET_DIR, Config.TARGET_FILE_NAME))
                                status_text.value = "تم حقن الباتش وتفعيله بنجاح تام! ✅"
                                status_text.color = ft.colors.GREEN_400
                            except Exception:
                                status_text.value = "فشل النقل! تأكد من تفعيل صلاحيات Shizuku على جهازك."
                                status_text.color = ft.colors.RED_400
                    else:
                        status_text.value = "فشل تحميل ملف الباتش من الرابط الخارجي!"
                        status_text.color = ft.colors.RED_400

                elif status == "banned":
                    status_text.value = "عذراً، هذا الكود محظور نهائياً (Banned) ❌"
                    status_text.color = ft.colors.RED_400
                else:
                    status_text.value = res_data.get("message", "الكود غير صالح أو منتهي!")
                    status_text.color = ft.colors.RED_400

            except requests.exceptions.ConnectionError:
                status_text.value = "تعذر الاتصال بالسيرفر، تأكد من اتصال الإنترنت."
                status_text.color = ft.colors.RED_400
            except Exception as ex:
                status_text.value = f"حدث خطأ غير متوقع: {str(ex)}"
                status_text.color = ft.colors.RED_400

            progress_bar.visible = False
            action_btn.disabled = False
            page.update()

        # تشغيل العملية في الخلفية لمنع تهنيج الواجهة (حماية من خطأ ANR)
        threading.Thread(target=background_task).start()

    action_btn = ft.ElevatedButton(
        text="تحقق وفعل الباتش",
        icon=ft.Icons.SECURITY,
        on_click=process_activation,
        bgcolor=ft.colors.RED_900,
        color=ft.colors.WHITE,
        width=320
    )

    page.add(
        ft.Container(
            content=ft.Column(
                [
                    ft.Text("PUBG VIP Control Panel", size=20, weight=ft.FontWeight.BOLD, color=ft.colors.AMBER_ACCENT),
                    ft.Divider(height=25, color=ft.colors.TRANSPARENT),
                    key_input,
                    ft.Divider(height=15, color=ft.colors.TRANSPARENT),
                    action_btn,
                    ft.Divider(height=25, color=ft.colors.TRANSPARENT),
                    progress_bar,
                    ft.Divider(height=10, color=ft.colors.TRANSPARENT),
                    status_text,
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=20,
            alignment=ft.alignment.center,
        )
    )

# التصحيح النهائي المتوافق تماماً مع Flet لتفادي خطأ الـ AttributeError
if __name__ == "__main__":
    ft.app(main)
