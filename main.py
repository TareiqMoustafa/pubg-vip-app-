import flet as ft
import requests
import os
import threading

def main(page: ft.Page):
    page.title = "PUBG VIP Manager Pro"
    page.theme_mode = ft.ThemeMode.DARK
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.window_width = 400
    page.window_height = 650

    # رابط سيرفرك على Vercel للتحقق من الأكواد
    SERVER_URL = "https://pak-license-server.vercel.app"
    
    # رابط تحميل الباتش المباشر من Catbox
    PATCH_DOWNLOAD_URL = "https://files.catbox.moe/nwnc4y.pak"
    
    # اسم الملف النهائي المطابق تماماً لمتطلبات اللعبة
    TARGET_FILE_NAME = "res_pufferpatch_4.6.1.21589.pak"

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
                # 1. التحقق من الكود عبر سيرفر Vercel
                res = requests.post(f"{SERVER_URL}/api/verify", json={"key": key, "device_id": "android_device_01"}, timeout=10)
                res_data = res.json()
                status = res_data.get("status")

                if status == "active":
                    status_text.value = "الكود صالح! جاري تحميل ملف الباتش..."
                    page.update()

                    # 2. تحميل الباتش من Catbox
                    patch_res = requests.get(PATCH_DOWNLOAD_URL, stream=True, timeout=25)
                    
                    if patch_res.status_code == 200:
                        # 3. مسار حفظ الباتش في مجلد لعبة ببجي الرسمي
                        target_dir = "/storage/emulated/0/Android/data/com.tencent.ig/files/UE4Game/ShadowTrackerExtra/ShadowTrackerExtra/Saved/Paks/"
                        
                        if os.path.exists(target_dir) or os.access("/storage/emulated/0/", os.W_OK):
                            os.makedirs(target_dir, exist_ok=True)
                            file_path = os.path.join(target_dir, TARGET_FILE_NAME)
                            
                            # حفظ الملف بالاسم الدقيق تلقائياً
                            with open(file_path, "wb") as f:
                                for chunk in patch_res.iter_content(chunk_size=1024):
                                    if chunk:
                                        f.write(chunk)
                                        
                            status_text.value = "تم تحميل وحقن الباتش بالاسم المطلوب بنجاح! ✅"
                            status_text.color = ft.colors.GREEN_400
                        else:
                            status_text.value = "تم التحميل! يتطلب أندرويد 11+ تفعيل Shizuku للنقل."
                            status_text.color = ft.colors.ORANGE_400
                    else:
                        status_text.value = "فشل تحميل ملف الباتش من الرابط الخارجي!"
                        status_text.color = ft.colors.RED_400

                elif status == "banned":
                    status_text.value = "عذراً، هذا الكود محظور نهائياً (Banned) ❌"
                    status_text.color = ft.colors.RED_400
                else:
                    status_text.value = res_data.get("message", "الكود غير صالح!")
                    status_text.color = ft.colors.RED_400

            except requests.exceptions.ConnectionError:
                status_text.value = "تعذر الاتصال بالسيرفر، تأكد من الإنترنت."
                status_text.color = ft.colors.RED_400
            except Exception as ex:
                status_text.value = f"خطأ غير متوقع: {str(ex)}"
                status_text.color = ft.colors.RED_400

            progress_bar.visible = False
            action_btn.disabled = False
            page.update()

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

ft.app(target=main)
