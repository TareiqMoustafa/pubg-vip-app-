"""الإعدادات المركزية - عدّل القيم هنا فقط.

رابط الباتش لا يُكتب هنا في الغالب: ضعه من لوحة التحكم (/admin ← الإعدادات ← ملف الباتش)
فيصل للتطبيق تلقائياً بدون إعادة بناء. القيمة أدناه احتياطية فقط إن لم يرسل السيرفر رابطاً.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    # نسخة التطبيق (يجب أن تطابق version في pyproject.toml)
    APP_VERSION: str = "1.3.0"

    # سيرفر التحقق
    SERVER_URL: str = "https://pak-license-server.vercel.app"
    VERIFY_ENDPOINT: str = "/api/verify"
    APP_CONFIG_ENDPOINT: str = "/api/app-config"

    # ملف الباتش (احتياطي؛ الأصل من لوحة التحكم)
    PATCH_DOWNLOAD_URL: str = "https://files.catbox.moe/nwnc4y.pak"
    # روابط بديلة تُجرَّب تلقائياً إذا فشل الرابط الأساسي (GitHub Releases مثلاً)
    PATCH_MIRRORS: tuple = ()
    PATCH_SHA256: str = ""  # اختياري: ضع هنا بصمة SHA-256 للتحقق من سلامة الملف
    TARGET_FILE_NAME: str = "res_pufferpatch_4.6.1.21589.pak"
    TARGET_DIR: str = (
        "/storage/emulated/0/Android/data/com.tencent.ig/files/UE4Game/"
        "ShadowTrackerExtra/ShadowTrackerExtra/Saved/Paks/"
    )

    # الشبكة
    VERIFY_TIMEOUT: float = 20.0
    DOWNLOAD_TIMEOUT: float = 300.0
    DOWNLOAD_RETRIES: int = 3
    CHUNK_SIZE: int = 64 * 1024
    USER_AGENT: str = (
        "Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36"
    )

    # الواجهة
    APP_TITLE: str = "PUBG VIP Manager"


CFG = Config()
