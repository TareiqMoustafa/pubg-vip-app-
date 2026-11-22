"""الإعدادات المركزية للتطبيق — عدّل القيم الأساسية من هنا بسهولة."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    # هوية التطبيق والمطور
    APP_TITLE: str = "PUBG VIP Manager"
    APP_VERSION: str = "2.0.2"
    DEVELOPER_NAME: str = "Tareiq"
    DEVELOPER_TAGLINE: str = "Engineered by Tareiq"

    # سيرفر التحقق
    SERVER_URL: str = "https://pak-license-server.vercel.app"
    VERIFY_ENDPOINT: str = "/api/verify"
    APP_CONFIG_ENDPOINT: str = "/api/app-config"
    HEALTH_ENDPOINT: str = "/api/health"

    # ملف/أرشيف الباتش الاحتياطي (الأصل يُجلب ديناميكياً من لوحة التحكم)
    PATCH_DOWNLOAD_URL: str = "https://files.catbox.moe/nwnc4y.pak"
    PATCH_MIRRORS: tuple = ()
    PATCH_SHA256: str = ""
    TARGET_FILE_NAME: str = "res_pufferpatch_4.6.1.21589.pak"
    FALLBACK_FOLDER_NAME: str = "vip_patch_folder"
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
        "Mozilla/5.0 (Linux; Android 14; Mobile) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Mobile Safari/537.36"
    )


CFG = Config()
