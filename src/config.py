"""إعدادات وثوابت تطبيق Lader Tareiq."""
from __future__ import annotations

import os

APP_TITLE: str = "Lader Tareiq"
DEVELOPER_NAME: str = "Lader Tareiq"
DEVELOPER_TAGLINE: str = "Smart License • OTA • Resource Engine"
APP_VERSION: str = "2.2.1"
OTA_VERSION: str = "1.0.0"

SERVER_URL: str = os.environ.get(
    "LADER_SERVER_URL",
    "https://pak-license-server.vercel.app",
).rstrip("/")

DEFAULT_SUPPORT_URL: str = "https://t.me/LaderTareiqSupport"
DEFAULT_UPDATE_URL: str = ""
DEFAULT_GAME_PACKAGE: str = "com.tencent.ig"
DEFAULT_TARGET_FILE: str = "res_pufferpatch.pak"
DEFAULT_DEPLOY_MODE: str = "auto"

REQUEST_TIMEOUT: float = 10.0
DOWNLOAD_TIMEOUT: float = 45.0
MAX_DOWNLOAD_BYTES: int = 512 * 1024 * 1024

COLOR_BG: str = "#05070E"
COLOR_BG_ALT: str = "#0B1024"
COLOR_CARD: str = "#0E152E"
COLOR_CARD_BORDER: str = "#1E2D58"
COLOR_CYAN: str = "#19E3FF"
COLOR_VIOLET: str = "#8B5CFF"
COLOR_PINK: str = "#FF2E93"
COLOR_GREEN: str = "#38FFA2"
COLOR_AMBER: str = "#FFB020"
COLOR_TEXT: str = "#EEF3FF"
COLOR_MUTED: str = "#8A98C2"
