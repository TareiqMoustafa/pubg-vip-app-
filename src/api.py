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
    EXPIRED = "expired"
    INVALID = "invalid"
    DEVICE_LIMIT = "device_limit"
    UPDATE_REQUIRED = "update_required"
    MAINTENANCE = "maintenance"
    NETWORK_ERROR = "network_error"
    SERVER_ERROR = "server_error"


@dataclass
class LicenseResult:
    status: LicenseStatus
    message: str = ""
    download_url: str = ""
    target_file_name: str = ""
    game_package: str = ""
    patch_version: str = ""
    force_update: bool = False
    license_type: str = ""
    expires_at: str = ""
    remaining_days: int = 0
    total_days: int = 0
    notice: str = ""
    support_url: str = ""
    update_url: str = ""
    patch_sha256: str = ""
    patch_notes: str = ""


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


def _int(v, default: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


async def fetch_app_config() -> dict:
    """إعلان/رابط دعم/وضع الصيانة قبل إدخال الكود. يفشل بصمت (يرجع {})."""
    url = CFG.SERVER_URL.rstrip("/") + CFG.APP_CONFIG_ENDPOINT
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            res = await client.get(url)
        data = res.json()
        return data if isinstance(data, dict) else {}
    except (httpx.HTTPError, ValueError):
        return {}


async def verify_license(key: str) -> LicenseResult:
    url = CFG.SERVER_URL.rstrip("/") + CFG.VERIFY_ENDPOINT
    payload = {"key": key, "device_id": get_device_id(), "app_version": CFG.APP_VERSION}
    try:
        async with httpx.AsyncClient(timeout=CFG.VERIFY_TIMEOUT) as client:
            res = await client.post(url, json=payload)
        data = res.json()
    except (httpx.ConnectError, httpx.TimeoutException):
        return LicenseResult(LicenseStatus.NETWORK_ERROR, "تعذر الاتصال بالسيرفر، تأكد من الإنترنت.")
    except ValueError:
        return LicenseResult(LicenseStatus.SERVER_ERROR, "رد غير صالح من السيرفر.")
    except httpx.HTTPError as ex:
        return LicenseResult(LicenseStatus.SERVER_ERROR, f"خطأ في الشبكة: {ex}")
    if not isinstance(data, dict):
        return LicenseResult(LicenseStatus.SERVER_ERROR, "رد غير صالح من السيرفر.")

    status = data.get("status")
    message = data.get("message") or ""
    if status == "active":
        return LicenseResult(
            LicenseStatus.ACTIVE, message,
            download_url=data.get("download_url") or "",
            target_file_name=data.get("target_file_name") or "",
            game_package=data.get("game_package") or "",
            patch_version=str(data.get("patch_version") or ""),
            force_update=bool(data.get("force_update")),
            license_type=str(data.get("type") or ""),
            expires_at=str(data.get("expires_at") or ""),
            remaining_days=_int(data.get("remaining_days")),
            total_days=_int(data.get("total_days")),
            notice=data.get("notice") or "",
            support_url=data.get("support_url") or "",
            patch_sha256=str(data.get("patch_sha256") or ""),
            patch_notes=str(data.get("patch_notes") or ""),
        )
    if status == "banned":
        return LicenseResult(LicenseStatus.BANNED, "هذا الكود محظور نهائياً.")
    if status == "expired":
        return LicenseResult(LicenseStatus.EXPIRED, message or "انتهى الاشتراك، يرجى التجديد.")
    if status == "device_limit":
        return LicenseResult(LicenseStatus.DEVICE_LIMIT, message or "الكود مرتبط بجهاز آخر.")
    if status == "update_required":
        return LicenseResult(LicenseStatus.UPDATE_REQUIRED, message or "يجب تحديث التطبيق.",
                             update_url=data.get("update_url") or "")
    if status == "maintenance":
        return LicenseResult(LicenseStatus.MAINTENANCE, message or "السيرفر تحت الصيانة.")
    return LicenseResult(LicenseStatus.INVALID, message or "الكود غير صالح أو منتهي.")
