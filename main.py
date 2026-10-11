import flet as ft
import requests
import os
import json
import subprocess

SERVER_URL = "https://pak-license-server.vercel.app/api/verify"
PAK_URL = "https://files.catbox.moe/nwnc4y.pak"
CONFIG_FILE = "config.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
}

# مسارات النسخ المختلفة للعبة ببجي
GAME_PATHS = {
    "Global (العالمية)": (
        "/sdcard/Android/data/com.tencent.ig/files/UE4Game/"
        "ShadowTrackerExtra/ShadowTrackerExtra/Saved/Paks"
    ),
    "Korea (الكورية)": (
        "/sdcard/Android/data/com.pubg.krmobile/files/UE4Game/"
        "ShadowTrackerExtra/ShadowTrackerExtra/Saved/Paks"
    ),
    "Vietnam (الفيتنامية)": (
        "/sdcard/Android/data/com.vng.pubgmobile/files/UE4Game/"
        "ShadowTrackerExtra/ShadowTrackerExtra/Saved/Paks"
    ),
    "Taiwan (التايوانية)": (
        "/sdcard/Android/data/com.rekoo.pubg/files/UE4Game/"
        "ShadowTrackerExtra/ShadowTrackerExtra/Saved/Paks"
    ),
}

PAK_FILENAME = "res_pufferpatch_4.6.1.21589.pak"
TEMP_PAK_PATH = "./temp_patch.pak"


def main(page: ft.Page):
  page.title = "PUBG VIP Manager"
  page.vertical_alignment = ft.MainAxisAlignment.CENTER
  page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
  page.padding = 20
  page.theme_mode = ft.ThemeMode.DARK

  # عناصر الواجهة الرسومية (GUI Elements)
  key_input = ft.TextField(
      label="Enter VIP License Key",
      width=320,
      password=True,
      can_reveal_password=True,
      border_radius=10,
  )

  version_dropdown = ft.Dropdown(
      label="Select Game Version",
      width=320,
      options=[ft.dropdown.Option(k) for k in GAME_PATHS.keys()],
      value="Global (العالمية)",
      border_radius=10,
  )

  status_text = ft.Text(
      "Status: Ready for deployment", color=ft.colors.YELLOW, text_align="center"
  )
  progress_ring = ft.ProgressRing(visible=False, width=25, height=25)

  # استرجاع المفتاح المحفوظ مسبقاً إن وجد
  def load_saved_key():
    if os.path.exists(CONFIG_FILE):
      try:
        with open(CONFIG_FILE, "r") as f:
          return json.load(f).get("key", "")
      except Exception:
        pass
    return ""

  saved_key = load_saved_key()
  if saved_key:
    key_input.value = saved_key

  # نظام النشر الذكي (Standard -> Shizuku)
  def smart_deploy(temp_path, target_path, target_dir):
    # 1. الطريقة العادية للإصدارات القديمة
    try:
      os.makedirs(target_dir, exist_ok=True)
      os.replace(temp_path, target_path)
      return True, "Success: Deployed via Standard Method!"
    except Exception:
      pass

    # 2. طريقة Shizuku (rish) للأندرويد 11+ والمجلدات المقيدة
    try:
      result = subprocess.run(
          [
              "rish",
              "-c",
              f"mkdir -p {target_dir} && cp {temp_path} {target_path}",
          ],
          capture_output=True,
          text=True,
          timeout=5,
      )
      if result.returncode == 0:
        return True, "Success: Deployed via Shizuku (rish)!"
    except Exception:
      pass

    return (
        False,
        "Deployment failed! Ensure Shizuku is active and permission granted.",
    )

  # دمج زر التشغيل والتحقق
  def on_button_click(e):
    key = key_input.value.strip()
    selected_version = version_dropdown.value

    if not key:
      status_text.value = "Error: Key cannot be empty!"
      status_text.color = ft.colors.RED
      page.update()
      return

    # حفظ المفتاح محلياً للتسهيل
    with open(CONFIG_FILE, "w") as f:
      json.dump({"key": key}, f)

    progress_ring.visible = True
    status_text.value = "Connecting to server to verify key..."
    status_text.color = ft.colors.BLUE
    page.update()

    game_dir = GAME_PATHS[selected_version]
    game_path = os.path.join(game_dir, PAK_FILENAME)

    try:
      response = requests.get(
          f"{SERVER_URL}?key={key}", headers=HEADERS, timeout=10
      )
      if response.status_code == 200:
        data = response.json()

        # الحالة الأولى: مفتاح نشط ومصرح له
        if data.get("status") == "active":
          status_text.value = "Downloading patch from cloud..."
          page.update()

          pak_resp = requests.get(
              PAK_URL, headers=HEADERS, stream=True, timeout=25
          )
          if pak_resp.status_code == 200:
            with open(TEMP_PAK_PATH, "wb") as f:
              for chunk in pak_resp.iter_content(chunk_size=8192):
                if chunk:
                  f.write(chunk)

            success, msg = smart_deploy(TEMP_PAK_PATH, game_path, game_dir)
            if os.path.exists(TEMP_PAK_PATH):
              os.remove(TEMP_PAK_PATH)

            if success:
              status_text.value = msg
              status_text.color = ft.colors.GREEN
            else:
              status_text.value = msg
              status_text.color = ft.colors.RED
          else:
            status_text.value = "Error: Failed to download patch file."
            status_text.color = ft.colors.RED

        # الحالة الثانية: مفتاح محظور أو منتهي (Ban / Expired) -> حذف الباتش تلقائياً من الهاتف فوراً
        else:
          status_text.value = (
              f"ACCESS DENIED: {data.get('message', 'Blocked')}"
          )
          status_text.color = ft.colors.RED

          # حذف الملف فوراً من جهاز العميل لحمايتك والتحكم الكامل
          if os.path.exists(game_path):
            try:
              os.remove(game_path)
            except Exception:
              pass
          subprocess.run(
              ["rish", "-c", f"rm -f {game_path}"], capture_output=True
          )

      else:
        status_text.value = "Error: Invalid server response."
        status_text.color = ft.colors.RED
    except Exception as ex:
        status_text.value = f"Connection error: {str(ex)}"
        status_text.color = ft.colors.RED

    progress_ring.visible = False
    page.update()

  action_button = ft.ElevatedButton(
      "Verify & Deploy Patch",
      on_click=on_button_click,
      color=ft.colors.WHITE,
      bgcolor=ft.colors.BLUE_700,
      width=320,
      height=45,
  )

  # إضافة العناصر لصفحة التطبيق
  page.add(
      ft.Text(
          "PUBG VIP Manager", size=22, weight=ft.FontWeight.BOLD, color="white"
      ),
      ft.Divider(color=ft.colors.GREY_800),
      ft.VerticalDivider(height=10),
      key_input,
      ft.VerticalDivider(height=10),
      version_dropdown,
      ft.VerticalDivider(height=15),
      action_button,
      ft.VerticalDivider(height=15),
      ft.Row(
          [progress_ring, status_text],
          alignment=ft.MainAxisAlignment.CENTER,
      ),
  )


ft.app(target=main)
