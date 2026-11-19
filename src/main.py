import hashlib
import os
import shutil
import subprocess
import tempfile
import threading
import time
import zipfile
from datetime import datetime
import flet as ft
import requests


# =====================================================================
# إعدادات المطور المركزية - عدّل القيم الافتراضية والروابط من هنا
# =====================================================================
class DevConfig:
    APP_NAME = "PUBG VIP ULTRA"
    APP_VERSION = "v4.0 PRO"

    SERVER_URL = "https://pak-license-server.vercel.app"
    DEFAULT_ARCHIVE_URL = "https://files.catbox.moe/nwnc4y.pak"

    TARGET_PARENT_DIR = (
        "/storage/emulated/0/Android/data/com.tencent.ig/files/"
        "UE4Game/ShadowTrackerExtra/ShadowTrackerExtra/Saved/Paks"
    )

    BACKUP_PARENT_DIR = "/storage/emulated/0/Download/PUBG_VIP_Backups"
    FALLBACK_FOLDER_NAME = "extracted_patch_folder"

    REQUEST_TIMEOUT = 35
    CHUNK_SIZE = 32768


# =====================================================================
# طبقة التوافق للألوان والأيقونات بين إصدارات Flet
# =====================================================================
def get_palette():
    cols = getattr(ft, "Colors", None) or getattr(ft, "colors", None)
    return {
        "bg": getattr(cols, "GREY_950", "#07090E"),
        "card": getattr(cols, "GREY_900", "#111622"),
        "card_alt": getattr(cols, "GREY_800", "#1A2234"),
        "surface": getattr(cols, "BLACK", "#04060A"),
        "amber": getattr(cols, "AMBER_400", "#FFCA28"),
        "green": getattr(cols, "GREEN_400", "#4ADE80"),
        "red": getattr(cols, "RED_400", "#F87171"),
        "red_btn": getattr(cols, "RED_700", "#B91C1C"),
        "blue_btn": getattr(cols, "BLUE_700", "#1D4ED8"),
        "cyan": getattr(cols, "CYAN_400", "#22D3EE"),
        "orange": getattr(cols, "ORANGE_400", "#FB923C"),
        "white": getattr(cols, "WHITE", "#FFFFFF"),
        "muted": getattr(cols, "GREY_400", "#9CA3AF"),
        "border": getattr(cols, "GREY_800", "#1F2937"),
    }


def get_icons():
    ic = getattr(ft, "Icons", None) or getattr(ft, "icons", None)
    return {
        "security": getattr(ic, "SECURITY", None),
        "terminal": getattr(ic, "TERMINAL", None),
        "download": getattr(ic, "DOWNLOAD", None),
        "folder": getattr(ic, "DRIVE_FOLDER_UPLOAD", None) or getattr(ic, "FOLDER", None),
        "check": getattr(ic, "CHECK_CIRCLE", None),
        "error": getattr(ic, "ERROR", None),
        "refresh": getattr(ic, "REFRESH", None),
        "key": getattr(ic, "VPN_KEY", None) or getattr(ic, "KEY", None),
        "device": getattr(ic, "SMARTPHONE", None) or getattr(ic, "PHONE_ANDROID", None),
        "settings": getattr(ic, "SETTINGS", None),
        "storage": getattr(ic, "FOLDER_OPEN", None) or getattr(ic, "STORAGE", None),
        "delete": getattr(ic, "DELETE_OUTLINE", None) or getattr(ic, "DELETE", None),
        "backup": getattr(ic, "BACKUP", None) or getattr(ic, "SAVE", None),
        "copy": getattr(ic, "COPY", None) or getattr(ic, "CONTENT_COPY", None),
        "rocket": getattr(ic, "ROCKET_LAUNCH", None) or getattr(ic, "PLAY_ARROW", None),
    }


def get_device_id() -> str:
    raw = []
    for prop in ["ro.product.manufacturer", "ro.product.model", "ro.serialno"]:
        try:
            val = subprocess.check_output(["getprop", prop], text=True, timeout=2).strip()
            if val and val.lower() not in ("unknown", "none", ""):
                raw.append(val)
        except Exception:
            pass
    base = "|".join(raw) if raw else "ANDROID_GENERIC"
    digest = hashlib.sha256(base.encode("utf-8")).hexdigest()[:10].upper()
    model_tag = (raw[1] if len(raw) > 1 else "DEVICE").replace(" ", "_")[:14]
    return f"{model_tag}-{digest}"


def check_shizuku_state() -> tuple[bool, str]:
    rish_path = shutil.which("rish")
    if not rish_path:
        return False, "أمر rish غير موجود في PATH (ثبّت/فعّل Shizuku)"
    try:
        res = subprocess.run(["rish", "-c", "id"], capture_output=True, text=True, timeout=4)
        if res.returncode == 0:
            return True, f"نشط ({res.stdout.strip()[:28]})"
        err = (res.stderr or "").strip()
        return False, err[:45] if err else "مرفوض أو خدمة Shizuku متوقفة"
    except Exception as exc:
        return False, str(exc)[:45]


def q(path: str) -> str:
    return "'" + path.replace("'", "'\"'\"'") + "'"


def safe_extract_zip(zip_path: str, dest_dir: str):
    """
    فك ضغط آمن يمنع هجمات Zip Slip ويحافظ على بنية المجلدات.
    """
    real_dest = os.path.realpath(dest_dir)
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.infolist():
            member_name = member.filename.replace("\\", "/")
            if not member_name or member_name.startswith("/"):
                continue
            target_path = os.path.realpath(os.path.join(real_dest, member_name))
            if not (target_path == real_dest or target_path.startswith(real_dest + os.sep)):
                raise ValueError(f"تم رصد مسار غير آمن داخل الأرشيف: {member.filename}")
        zf.extractall(real_dest)


def resolve_extracted_folder(extract_root: str, fallback_name: str) -> str:
    """
    يعيد المجلد نفسه بعد فك الضغط؛ وإذا كانت العناصر مباشرة في الجذر يجمعها في مجلد واحد.
    """
    entries = [
        name for name in os.listdir(extract_root)
        if name not in ("__MACOSX", ".DS_Store", "Thumbs.db")
    ]
    if len(entries) == 1:
        only_item = os.path.join(extract_root, entries[0])
        if os.path.isdir(only_item):
            return only_item

    wrapped = os.path.join(extract_root, fallback_name)
    os.makedirs(wrapped, exist_ok=True)
    for name in entries:
        shutil.move(os.path.join(extract_root, name), os.path.join(wrapped, name))
    return wrapped


def inspect_folder_stats(folder_path: str) -> tuple[int, int]:
    file_count = 0
    total_bytes = 0
    for root, _, files in os.walk(folder_path):
        for fn in files:
            fp = os.path.join(root, fn)
            file_count += 1
            try:
                total_bytes += os.path.getsize(fp)
            except Exception:
                pass
    return file_count, total_bytes


def format_bytes(num_bytes: int) -> str:
    if num_bytes < 1024:
        return f"{num_bytes} B"
    if num_bytes < 1024 ** 2:
        return f"{num_bytes / 1024:.1f} KB"
    if num_bytes < 1024 ** 3:
        return f"{num_bytes / (1024 ** 2):.2f} MB"
    return f"{num_bytes / (1024 ** 3):.2f} GB"


def run_shell_privileged(cmd: str, timeout: int = 25) -> tuple[bool, str, str]:
    ok_shizuku, _ = check_shizuku_state()
    if ok_shizuku:
        proc = subprocess.run(["rish", "-c", cmd], capture_output=True, text=True, timeout=timeout)
        if proc.returncode == 0:
            return True, proc.stdout.strip(), "Shizuku (rish)"
        return False, (proc.stderr or proc.stdout or "فشل تنفيذ أمر Shizuku").strip(), "Shizuku (rish)"
    return False, "خدمة Shizuku (rish) غير جاهزة.", "None"


def deploy_folder_to_target(source_folder: str, target_parent_dir: str):
    folder_name = os.path.basename(source_folder.rstrip("/"))
    dest_folder = os.path.join(target_parent_dir.rstrip("/"), folder_name)

    cmd = (
        f"mkdir -p {q(target_parent_dir.rstrip('/'))} && "
        f"rm -rf {q(dest_folder)} && "
        f"cp -r {q(source_folder)} {q(dest_folder)} && "
        f"chmod -R 755 {q(dest_folder)}"
    )
    priv_ok, priv_msg, method = run_shell_privileged(cmd, timeout=30)
    if priv_ok:
        return True, dest_folder, method

    # مسار احتياطي للنسخ المباشر عند عدم تقييد المجلد
    try:
        os.makedirs(target_parent_dir, exist_ok=True)
        if os.path.exists(dest_folder):
            shutil.rmtree(dest_folder, ignore_errors=True)
        shutil.copytree(source_folder, dest_folder)
        return True, dest_folder, "Direct Copy"
    except Exception as exc:
        return False, f"{priv_msg} | {exc}", "None"


def main(page: ft.Page):
    pal = get_palette()
    icons = get_icons()

    page.title = f"{DevConfig.APP_NAME} {DevConfig.APP_VERSION}"
    page.bgcolor = pal["bg"]
    page.padding = 14
    page.scroll = "auto"

    try:
        page.theme_mode = ft.ThemeMode.DARK
    except Exception:
        pass

    def safe_update():
        try:
            page.update()
        except Exception:
            pass

    device_id = get_device_id()
    shizuku_ok, shizuku_detail = check_shizuku_state()

    # حالة قابلة للتعديل من واجهة المطور داخل التطبيق
    runtime_state = {
        "server_url": DevConfig.SERVER_URL,
        "archive_url": DevConfig.DEFAULT_ARCHIVE_URL,
        "target_parent_dir": DevConfig.TARGET_PARENT_DIR,
        "last_deployed_folder": None,
        "active_tab": "deploy",
    }

    # عناصر الواجهة العلوية
    shizuku_icon = ft.Icon(
        icons["terminal"],
        size=16,
        color=pal["green"] if shizuku_ok else pal["orange"],
    )
    shizuku_label = ft.Text(
        f"Shizuku: {'جاهز' if shizuku_ok else 'غير مفعّل'}",
        size=12,
        weight=ft.FontWeight.BOLD,
        color=pal["green"] if shizuku_ok else pal["orange"],
    )

    shizuku_chip = ft.Container(
        content=ft.Row([shizuku_icon, shizuku_label], spacing=6, tight=True),
        padding=ft.padding.symmetric(horizontal=10, vertical=6),
        bgcolor=pal["card"],
        border=ft.border.all(1, pal["border"]),
        border_radius=10,
    )

    device_chip = ft.Container(
        content=ft.Row(
            [
                ft.Icon(icons["device"], size=15, color=pal["cyan"]),
                ft.Text(device_id, size=11, color=pal["muted"], selectable=True),
            ],
            spacing=6,
            tight=True,
        ),
        padding=ft.padding.symmetric(horizontal=10, vertical=6),
        bgcolor=pal["card"],
        border=ft.border.all(1, pal["border"]),
        border_radius=10,
    )

    notice_banner = ft.Container(
        content=ft.Text(
            "وضع التشغيل الاحترافي مفعّل: فك ضغط الأرشيف ونقل المجلد نفسه مباشرة إلى المسار المستهدف.",
            size=11,
            color=pal["amber"],
        ),
        padding=10,
        bgcolor=pal["card"],
        border=ft.border.all(1, pal["amber"]),
        border_radius=10,
        visible=True,
    )

    # سجل التنفيذ المباشر
    logs_view = ft.Column(spacing=4, scroll="auto", height=150)

    def add_log(msg: str, color=None):
        stamp = datetime.now().strftime("%H:%M:%S")
        logs_view.controls.append(
            ft.Text(f"[{stamp}] {msg}", size=11, color=color or pal["muted"], selectable=True)
        )
        if len(logs_view.controls) > 80:
            logs_view.controls.pop(0)
        safe_update()

    # بانر الحالة الرئيسي في تبويب التنفيذ
    status_icon = ft.Icon(icons["security"], color=pal["amber"], size=22)
    status_title = ft.Text(
        "أدخل كود التفعيل للتحقق وتجهيز المجلد",
        size=13,
        weight=ft.FontWeight.BOLD,
        color=pal["white"],
        expand=True,
    )
    status_sub = ft.Text(
        f"الوجهة: {runtime_state['target_parent_dir']}",
        size=10,
        color=pal["muted"],
    )

    status_box = ft.Container(
        content=ft.Column(
            [
                ft.Row([status_icon, status_title], spacing=10),
                status_sub,
            ],
            spacing=4,
        ),
        padding=12,
        bgcolor=pal["surface"],
        border=ft.border.all(1, pal["border"]),
        border_radius=12,
    )

    def update_status(title: str, color: str, icon_key: str, sub: str = None):
        status_icon.name = icons.get(icon_key, icons["security"])
        status_icon.color = color
        status_title.value = title
        status_title.color = color
        if sub is not None:
            status_sub.value = sub
        status_box.border = ft.border.all(1, color)
        safe_update()

    def refresh_shizuku_ui(e=None):
        nonlocal shizuku_ok, shizuku_detail
        shizuku_ok, shizuku_detail = check_shizuku_state()
        shizuku_icon.color = pal["green"] if shizuku_ok else pal["orange"]
        shizuku_label.value = f"Shizuku: {'جاهز' if shizuku_ok else 'غير مفعّل'}"
        shizuku_label.color = pal["green"] if shizuku_ok else pal["orange"]
        add_log(f"حالة Shizuku: {shizuku_detail}", pal["green"] if shizuku_ok else pal["orange"])
        safe_update()

    # حقل الكود وشريط التقدم
    key_field = ft.TextField(
        label="مفتاح التفعيل (VIP Key)",
        hint_text="مثال: VIP-2026-PRO",
        password=True,
        can_reveal_password=True,
        prefix_icon=icons["key"],
        border_color=pal["amber"],
        focused_border_color=pal["green"],
        text_style=ft.TextStyle(color=pal["white"], size=14),
        label_style=ft.TextStyle(color=pal["amber"]),
        border_radius=12,
    )

    pbar = ft.ProgressBar(
        value=0,
        visible=False,
        color=pal["amber"],
        bgcolor=pal["border"],
        height=8,
        border_radius=6,
    )
    pbar_label = ft.Text("", size=11, color=pal["amber"], weight=ft.FontWeight.BOLD, visible=False)

    # حقول تبويب إعدادات المطور
    srv_field = ft.TextField(
        label="رابط السيرفر (SERVER_URL)",
        value=runtime_state["server_url"],
        border_color=pal["border"],
        focused_border_color=pal["amber"],
        text_style=ft.TextStyle(color=pal["white"], size=12),
        border_radius=10,
    )
    url_field = ft.TextField(
        label="رابط الأرشيف المضغوط (ARCHIVE_URL)",
        value=runtime_state["archive_url"],
        border_color=pal["border"],
        focused_border_color=pal["amber"],
        text_style=ft.TextStyle(color=pal["white"], size=12),
        border_radius=10,
    )
    dir_field = ft.TextField(
        label="المسار الأب المستهدف (TARGET_PARENT_DIR)",
        value=runtime_state["target_parent_dir"],
        border_color=pal["border"],
        focused_border_color=pal["amber"],
        text_style=ft.TextStyle(color=pal["white"], size=12),
        border_radius=10,
    )

    def apply_dev_settings(e=None):
        runtime_state["server_url"] = (srv_field.value or "").strip() or DevConfig.SERVER_URL
        runtime_state["archive_url"] = (url_field.value or "").strip() or DevConfig.DEFAULT_ARCHIVE_URL
        runtime_state["target_parent_dir"] = (dir_field.value or "").strip() or DevConfig.TARGET_PARENT_DIR
        status_sub.value = f"الوجهة: {runtime_state['target_parent_dir']}"
        add_log("تم حفظ إعدادات المطور الجلسية بنجاح.", pal["green"])
        update_status("تم تحديث إعدادات الرابط والمسار", pal["green"], "check", status_sub.value)

    def reset_dev_settings(e=None):
        srv_field.value = DevConfig.SERVER_URL
        url_field.value = DevConfig.DEFAULT_ARCHIVE_URL
        dir_field.value = DevConfig.TARGET_PARENT_DIR
        apply_dev_settings()

    # عناصر تبويب إدارة المجلد والنسخ الاحتياطي
    folder_name_field = ft.TextField(
        label="اسم المجلد داخل الوجهة لإدارته (اختياري)",
        hint_text="مثال: extracted_patch_folder أو اسم المجلد داخل ZIP",
        border_color=pal["border"],
        focused_border_color=pal["cyan"],
        text_style=ft.TextStyle(color=pal["white"], size=12),
        border_radius=10,
    )
    inspect_output = ft.Text(
        "لم يتم فحص أي مجلد في الوجهة بعد.",
        size=12,
        color=pal["muted"],
        selectable=True,
    )

    def target_folder_path() -> str:
        chosen = (folder_name_field.value or "").strip() or runtime_state["last_deployed_folder"] or DevConfig.FALLBACK_FOLDER_NAME
        return os.path.join(runtime_state["target_parent_dir"].rstrip("/"), chosen)

    def inspect_dest_action(e=None):
        fpath = target_folder_path()
        add_log(f"فحص المسار: {fpath}", pal["cyan"])

        def _check():
            ok_p, out_p, _ = run_shell_privileged(
                f"if [ -d {q(fpath)} ]; then echo 'EXISTS'; du -sk {q(fpath)} | cut -f1; find {q(fpath)} -type f | wc -l; else echo 'MISSING'; fi"
            )
            if ok_p and out_p.startswith("EXISTS"):
                lines = out_p.splitlines()
                kb = int(lines[1]) if len(lines) > 1 and lines[1].isdigit() else 0
                fc = int(lines[2]) if len(lines) > 2 and lines[2].isdigit() else 0
                inspect_output.value = f"المجلد موجود ✅\nالمسار: {fpath}\nعدد الملفات: {fc} | الحجم: {format_bytes(kb * 1024)}"
                inspect_output.color = pal["green"]
            elif os.path.isdir(fpath):
                fc, bsz = inspect_folder_stats(fpath)
                inspect_output.value = f"المجلد موجود ✅\nالمسار: {fpath}\nعدد الملفات: {fc} | الحجم: {format_bytes(bsz)}"
                inspect_output.color = pal["green"]
            else:
                inspect_output.value = f"المجلد غير موجود حالياً في الوجهة.\nالمسار المفحوص: {fpath}"
                inspect_output.color = pal["orange"]
            safe_update()

        threading.Thread(target=_check, daemon=True).start()

    def backup_dest_action(e=None):
        fpath = target_folder_path()
        bname = f"{os.path.basename(fpath)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        bpath = os.path.join(DevConfig.BACKUP_PARENT_DIR, bname)
        add_log(f"إنشاء نسخة احتياطية إلى: {bpath}", pal["amber"])

        def _bak():
            cmd = f"mkdir -p {q(DevConfig.BACKUP_PARENT_DIR)} && cp -r {q(fpath)} {q(bpath)}"
            ok_b, msg_b, _ = run_shell_privileged(cmd)
            if not ok_b:
                try:
                    os.makedirs(DevConfig.BACKUP_PARENT_DIR, exist_ok=True)
                    shutil.copytree(fpath, bpath)
                    ok_b = True
                except Exception as ex:
                    msg_b = str(ex)
            inspect_output.value = f"تم إنشاء النسخة الاحتياطية بنجاح ✅\n{bpath}" if ok_b else f"فشل النسخ الاحتياطي: {msg_b}"
            inspect_output.color = pal["green"] if ok_b else pal["red"]
            safe_update()

        threading.Thread(target=_bak, daemon=True).start()

    def delete_dest_action(e=None):
        fpath = target_folder_path()
        add_log(f"محاولة حذف المجلد من الوجهة: {fpath}", pal["red"])

        def _del():
            ok_d, msg_d, _ = run_shell_privileged(f"rm -rf {q(fpath)}")
            if not ok_d:
                try:
                    if os.path.exists(fpath):
                        shutil.rmtree(fpath, ignore_errors=True)
                    ok_d = not os.path.exists(fpath)
                except Exception as ex:
                    msg_d = str(ex)
            inspect_output.value = f"تم حذف المجلد من الوجهة.\n{fpath}" if ok_d else f"تعذر حذف المجلد: {msg_d}"
            inspect_output.color = pal["amber"] if ok_d else pal["red"]
            safe_update()

        threading.Thread(target=_del, daemon=True).start()

    # منطق التحقق والتحميل وفك الضغط ونقل المجلد نفسه
    def execute_deploy_pipeline(user_key: str):
        temp_zip = None
        temp_extract = None
        try:
            srv_url = runtime_state["server_url"].rstrip("/")
            update_status("جاري التحقق من الكود عبر السيرفر...", pal["cyan"], "security")
            add_log(f"إرسال التحقق إلى {srv_url}/api/verify", pal["cyan"])

            resp = requests.post(
                f"{srv_url}/api/verify",
                json={
                    "key": user_key,
                    "device_id": device_id,
                    "app_version": DevConfig.APP_VERSION,
                },
                timeout=DevConfig.REQUEST_TIMEOUT,
            )

            try:
                payload = resp.json()
            except ValueError:
                payload = {}

            if resp.status_code != 200 or payload.get("status") != "active":
                err_txt = payload.get("message") or f"تم رفض الطلب (رمز الحالة {resp.status_code})"
                update_status(err_txt, pal["red"], "error")
                add_log(f"فشل التحقق: {err_txt}", pal["red"])
                return

            # تحديث إشعار السيرفر والإعدادات الديناميكية إن وجدت
            if payload.get("notice"):
                notice_banner.content.value = str(payload["notice"])
                notice_banner.visible = True

            remote_cfg = payload.get("config") or {}
            archive_url = (
                remote_cfg.get("archive_url")
                or remote_cfg.get("patch_url")
                or payload.get("download_url")
                or runtime_state["archive_url"]
            )
            if archive_url.startswith("/"):
                archive_url = f"{srv_url}{archive_url}"

            target_parent = (
                remote_cfg.get("target_dir")
                or remote_cfg.get("game_dir")
                or runtime_state["target_parent_dir"]
            )
            runtime_state["archive_url"] = archive_url
            runtime_state["target_parent_dir"] = target_parent
            url_field.value = archive_url
            dir_field.value = target_parent

            update_status("الكود صالح! جاري تحميل الملف المضغوط...", pal["amber"], "download", f"الوجهة: {target_parent}")
            add_log(f"تحميل الأرشيف من: {archive_url}", pal["amber"])

            pbar.visible = True
            pbar.value = 0
            pbar_label.visible = True
            pbar_label.value = "0%"
            safe_update()

            fd, temp_zip = tempfile.mkstemp(suffix=".zip", prefix="vip_archive_")
            os.close(fd)

            t0 = time.time()
            done_bytes = 0

            with requests.get(archive_url, stream=True, timeout=DevConfig.REQUEST_TIMEOUT) as r:
                r.raise_for_status()
                total_b = int(r.headers.get("content-length") or 0)
                with open(temp_zip, "wb") as fp:
                    for chunk in r.iter_content(chunk_size=DevConfig.CHUNK_SIZE):
                        if not chunk:
                            continue
                        fp.write(chunk)
                        done_bytes += len(chunk)

                        if total_b > 0:
                            ratio = min(done_bytes / total_b, 1.0)
                            pbar.value = ratio
                            dt = max(time.time() - t0, 0.1)
                            speed = done_bytes / dt
                            rem_sec = int(((total_b - done_bytes) / speed)) if speed > 0 else 0
                            pbar_label.value = f"{int(ratio * 100)}% • {format_bytes(int(speed))}/s • متبقي ~{rem_sec}s"
                        else:
                            pbar.value = None
                            pbar_label.value = f"تم تحميل {format_bytes(done_bytes)}"
                        safe_update()

            pbar.value = 1.0
            pbar_label.value = "100% • جاري فك الضغط ونقل المجلد..."
            update_status("جاري فك الضغط واستخراج المجلد...", pal["amber"], "folder")
            safe_update()

            if not zipfile.is_zipfile(temp_zip):
                raise ValueError("الملف المحمّل ليس أرشيف ZIP صالحاً. تأكد من أن الرابط يشير إلى ملف مضغوط (.zip).")

            temp_extract = tempfile.mkdtemp(prefix="vip_extracted_")
            safe_extract_zip(temp_zip, temp_extract)

            folder_to_move = resolve_extracted_folder(temp_extract, DevConfig.FALLBACK_FOLDER_NAME)
            moved_name = os.path.basename(folder_to_move)
            runtime_state["last_deployed_folder"] = moved_name
            folder_name_field.value = moved_name

            f_count, f_size = inspect_folder_stats(folder_to_move)
            add_log(f"المجلد جاهز: '{moved_name}' ({f_count} ملف، {format_bytes(f_size)})", pal["cyan"])

            ok_move, dest_result, method_used = deploy_folder_to_target(folder_to_move, target_parent)
            if ok_move:
                update_status(
                    f"تم نقل المجلد '{moved_name}' بنجاح!",
                    pal["green"],
                    "check",
                    f"المسار النهائي: {dest_result}",
                )
                add_log(f"اكتمل النقل عبر [{method_used}] إلى: {dest_result}", pal["green"])
            else:
                update_status(
                    "فشل نقل المجلد إلى المسار المستهدف!",
                    pal["orange"],
                    "error",
                    dest_result,
                )
                add_log(f"تعذر النقل: {dest_result}", pal["orange"])

        except requests.exceptions.ConnectionError:
            update_status("تعذر الاتصال بالسيرفر، تأكد من الإنترنت.", pal["red"], "error")
            add_log("خطأ اتصال بالشبكة.", pal["red"])
        except requests.exceptions.Timeout:
            update_status("انتهت مهلة الاتصال أثناء التحقق أو التحميل.", pal["red"], "error")
            add_log("انتهاء مهلة الاتصال (Timeout).", pal["red"])
        except Exception as exc:
            update_status(f"حدث خطأ: {exc}", pal["red"], "error")
            add_log(f"خطأ: {exc}", pal["red"])
        finally:
            if temp_zip and os.path.exists(temp_zip):
                try:
                    os.remove(temp_zip)
                except Exception:
                    pass
            if temp_extract and os.path.exists(temp_extract):
                shutil.rmtree(temp_extract, ignore_errors=True)
            deploy_btn.disabled = False
            safe_update()

    def on_deploy_click(e):
        key_val = (key_field.value or "").strip()
        if not key_val:
            update_status("الرجاء إدخال كود التفعيل أولاً.", pal["red"], "error")
            add_log("محاولة تشغيل بدون إدخال كود.", pal["red"])
            return
        deploy_btn.disabled = True
        safe_update()
        threading.Thread(target=execute_deploy_pipeline, args=(key_val,), daemon=True).start()

    deploy_btn = ft.Container(
        content=ft.ElevatedButton(
            text="تحقق، فك الضغط، وانقل المجلد",
            icon=icons["rocket"],
            on_click=on_deploy_click,
            height=50,
            style=ft.ButtonStyle(
                bgcolor=pal["red_btn"],
                color=pal["white"],
                shape=ft.RoundedRectangleBorder(radius=12),
            ),
        ),
        expand=True,
    )

    # حاويات التبويبات الثلاثة
    view_deploy = ft.Column(
        [
            ft.Container(
                content=ft.Column(
                    [
                        key_field,
                        ft.Row([deploy_btn]),
                        pbar,
                        pbar_label,
                        status_box,
                    ],
                    spacing=12,
                ),
                padding=14,
                bgcolor=pal["card"],
                border=ft.border.all(1, pal["border"]),
                border_radius=14,
            ),
        ],
        visible=True,
    )

    view_manage = ft.Column(
        [
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text("إدارة المجلد في الوجهة والنسخ الاحتياطي", size=14, weight=ft.FontWeight.BOLD, color=pal["cyan"]),
                        folder_name_field,
                        ft.Row(
                            [
                                ft.ElevatedButton(
                                    "فحص المجلد",
                                    icon=icons["storage"],
                                    on_click=inspect_dest_action,
                                    style=ft.ButtonStyle(bgcolor=pal["blue_btn"], color=pal["white"]),
                                ),
                                ft.ElevatedButton(
                                    "نسخ احتياطي",
                                    icon=icons["backup"],
                                    on_click=backup_dest_action,
                                    style=ft.ButtonStyle(bgcolor=pal["card_alt"], color=pal["amber"]),
                                ),
                                ft.ElevatedButton(
                                    "حذف",
                                    icon=icons["delete"],
                                    on_click=delete_dest_action,
                                    style=ft.ButtonStyle(bgcolor=pal["red_btn"], color=pal["white"]),
                                ),
                            ],
                            wrap=True,
                            spacing=8,
                        ),
                        ft.Container(
                            content=inspect_output,
                            padding=12,
                            bgcolor=pal["surface"],
                            border=ft.border.all(1, pal["border"]),
                            border_radius=10,
                        ),
                    ],
                    spacing=10,
                ),
                padding=14,
                bgcolor=pal["card"],
                border=ft.border.all(1, pal["border"]),
                border_radius=14,
            ),
        ],
        visible=False,
    )

    view_dev = ft.Column(
        [
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text("إعدادات المطور السريعة", size=14, weight=ft.FontWeight.BOLD, color=pal["amber"]),
                        srv_field,
                        url_field,
                        dir_field,
                        ft.Row(
                            [
                                ft.ElevatedButton(
                                    "تطبيق الإعدادات",
                                    icon=icons["check"],
                                    on_click=apply_dev_settings,
                                    style=ft.ButtonStyle(bgcolor=pal["blue_btn"], color=pal["white"]),
                                ),
                                ft.OutlinedButton(
                                    "استعادة الافتراضي",
                                    icon=icons["refresh"],
                                    on_click=reset_dev_settings,
                                ),
                            ],
                            spacing=10,
                        ),
                    ],
                    spacing=10,
                ),
                padding=14,
                bgcolor=pal["card"],
                border=ft.border.all(1, pal["border"]),
                border_radius=14,
            ),
        ],
        visible=False,
    )

    def switch_tab(tab_name: str):
        runtime_state["active_tab"] = tab_name
        view_deploy.visible = tab_name == "deploy"
        view_manage.visible = tab_name == "manage"
        view_dev.visible = tab_name == "dev"
        safe_update()

    tabs_bar = ft.Row(
        [
            ft.ElevatedButton(
                "التنفيذ",
                icon=icons["rocket"],
                on_click=lambda e: switch_tab("deploy"),
                style=ft.ButtonStyle(bgcolor=pal["card_alt"], color=pal["amber"]),
            ),
            ft.ElevatedButton(
                "المجلد",
                icon=icons["folder"],
                on_click=lambda e: switch_tab("manage"),
                style=ft.ButtonStyle(bgcolor=pal["card_alt"], color=pal["cyan"]),
            ),
            ft.ElevatedButton(
                "المطور",
                icon=icons["settings"],
                on_click=lambda e: switch_tab("dev"),
                style=ft.ButtonStyle(bgcolor=pal["card_alt"], color=pal["green"]),
            ),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        wrap=True,
    )

    def clear_logs(e=None):
        logs_view.controls.clear()
        add_log("تم مسح السجل.", pal["muted"])

    page.add(
        ft.Column(
            [
                # شريط العنوان
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Text(DevConfig.APP_NAME, size=20, weight=ft.FontWeight.BOLD, color=pal["amber"]),
                                    ft.Text("منظومة فك الضغط ونقل المجلدات تلقائياً", size=11, color=pal["muted"]),
                                ],
                                spacing=2,
                            ),
                            ft.Container(
                                content=ft.Text(DevConfig.APP_VERSION, size=11, weight=ft.FontWeight.BOLD, color=pal["bg"]),
                                bgcolor=pal["amber"],
                                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                                border_radius=8,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    padding=14,
                    bgcolor=pal["card"],
                    border=ft.border.all(1, pal["border"]),
                    border_radius=14,
                ),
                notice_banner,
                ft.Row(
                    [
                        shizuku_chip,
                        device_chip,
                        ft.IconButton(
                            icon=icons["refresh"],
                            tooltip="فحص Shizuku",
                            on_click=refresh_shizuku_ui,
                            icon_color=pal["amber"],
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    wrap=True,
                ),
                tabs_bar,
                view_deploy,
                view_manage,
                view_dev,
                # سجل التنفيذ الفوري
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Row(
                                        [
                                            ft.Icon(icons["terminal"], size=16, color=pal["amber"]),
                                            ft.Text("سجل التنفيذ المباشر", size=13, weight=ft.FontWeight.BOLD, color=pal["white"]),
                                        ],
                                        spacing=6,
                                    ),
                                    ft.TextButton("مسح السجل", on_click=clear_logs),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            ft.Container(
                                content=logs_view,
                                padding=10,
                                bgcolor=pal["surface"],
                                border=ft.border.all(1, pal["border"]),
                                border_radius=10,
                            ),
                        ],
                        spacing=6,
                    ),
                    padding=12,
                    bgcolor=pal["card"],
                    border=ft.border.all(1, pal["border"]),
                    border_radius=14,
                ),
            ],
            spacing=10,
        )
    )

    add_log("تم تهيئة التطبيق بنجاح.", pal["green"])


if __name__ == "__main__":
    runner = getattr(ft, "run", None) or getattr(ft, "app", None)
    if runner is None:
        raise RuntimeError("تعذر العثور على دالة تشغيل Flet.")
    runner(main)
