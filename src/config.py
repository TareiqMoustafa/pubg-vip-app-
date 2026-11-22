"""الإعدادات المركزية لتطبيق Lader Tareiq."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    # هوية التطبيق والمطور
    APP_TITLE: str = "Lader Tareiq"
    APP_VERSION: str = "2.1.0"
    OTA_VERSION: str = "1.0.0"
    DEVELOPER_NAME: str = "Lader Tareiq"
    DEVELOPER_TAGLINE: str = "Lader Tareiq • VIP Patch & Shizuku Suite"

    # سيرفر التحقق والتحديثات
    SERVER_URL: str = "https://pak-license-server.vercel.app"
    VERIFY_ENDPOINT: str = "/api/verify"
    APP_CONFIG_ENDPOINT: str = "/api/app-config"
    HEALTH_ENDPOINT: str = "/api/health"
    OTA_ENDPOINT: str = "/api/ota-bundle"

    # ملف/أرشيف الباتش الاحتياطي
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
    OTA_TIMEOUT: float = 25.0
    DOWNLOAD_RETRIES: int = 3
    CHUNK_SIZE: int = 64 * 1024
    USER_AGENT: str = (
        "Mozilla/5.0 (Linux; Android 14; Mobile) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Mobile Safari/537.36"
    )


CFG = Config()
