"""التعامل مع سيرفر التراخيص + معرّف الجهاز الثابت."""
from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import httpx

from config import CFG


class LicenseStatus(str, Enum):
    ACTIVE = "active"
    BANNED = "banned"
    INVALID = "invalid"
    NETWORK_ERROR = "network_error"
    SERVER_ERROR = "server_error"


@dataclass
class LicenseResult:
    status: LicenseStatus
    message: str = ""
    download_url: str = ""


def get_device_id() -> str:
    """معرّف فريد وثابت لكل تثبيت (بدل القيمة الثابتة لكل الأجهزة)."""
    base = Path(os.environ.get("FLET_APP_STORAGE_DATA") or Path.home())
    path = base / ".device_id"
    try:
        if path.exists():
            value = path.read_text().strip()
            if value:
                return value
        base.mkdir(parents=True, exist_ok=True)
        value = uuid.uuid4().hex
        path.write_text(value)
        return value
    except OSError:
        return uuid.uuid4().hex


async def verify_license(key: str) -> LicenseResult:
    url = CFG.SERVER_URL.rstrip("/") + CFG.VERIFY_ENDPOINT
    try:
        async with httpx.AsyncClient(timeout=CFG.VERIFY_TIMEOUT) as client:
            res = await client.post(url, json={"key": key, "device_id": get_device_id()})
        data = res.json()
    except (httpx.ConnectError, httpx.TimeoutException):
        return LicenseResult(LicenseStatus.NETWORK_ERROR, "تعذر الاتصال بالسيرفر، تأكد من الإنترنت.")
    except ValueError:
        return LicenseResult(LicenseStatus.SERVER_ERROR, "رد غير صالح من السيرفر.")
    except httpx.HTTPError as ex:
        return LicenseResult(LicenseStatus.SERVER_ERROR, f"خطأ في الشبكة: {ex}")

    status = data.get("status")
    if status == "active":
        return LicenseResult(LicenseStatus.ACTIVE, data.get("message", ""), data.get("download_url") or "")
    if status == "banned":
        return LicenseResult(LicenseStatus.BANNED, "هذا الكود محظور نهائياً.")
    return LicenseResult(LicenseStatus.INVALID, data.get("message") or "الكود غير صالح أو منتهي.")
