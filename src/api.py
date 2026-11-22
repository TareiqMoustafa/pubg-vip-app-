"""عميل الاتصال بالسيرفر والتحقق من التراخيص ومزامنة OTA."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import requests

from config import APP_VERSION, OTA_VERSION, REQUEST_TIMEOUT, SERVER_URL
from state import load as load_state


@dataclass
class ApiResult:
    ok: bool
    status_code: int
    data: dict[str, Any]
    message: str


def _parse_version_tuple(v: str) -> tuple[int, ...]:
    parts = re.findall(r"\d+", str(v or ""))
    if not parts:
        return (0,)
    return tuple(int(p) for p in parts[:4])


def is_newer_version(remote_ver: str, local_ver: str) -> bool:
    r_clean = str(remote_ver or "").strip()
    l_clean = str(local_ver or "").strip()
    if not r_clean or r_clean == l_clean:
        return False
    return _parse_version_tuple(r_clean) > _parse_version_tuple(l_clean)


def get_device_id() -> str:
    env_id = os.environ.get("ANDROID_ID") or os.environ.get("DEVICE_ID")
    if env_id:
        cleaned = re.sub(r"[^A-Za-z0-9_-]", "", env_id.strip())
        if len(cleaned) >= 8:
            return cleaned[:64]

    base = Path(os.environ.get("FLET_APP_STORAGE_DATA") or (Path.home() / ".lader_tareiq"))
    id_file = base / "device_id.txt"
    try:
        if id_file.exists():
            saved_id = re.sub(r"[^A-Za-z0-9_-]", "", id_file.read_text(encoding="utf-8").strip())
            if len(saved_id) >= 8:
                return saved_id[:64]
    except Exception:
        pass

    raw_seed = f"{platform.node()}|{platform.system()}|{platform.release()}|{uuid.getnode()}"
    digest = hashlib.sha256(raw_seed.encode("utf-8")).hexdigest()[:24]
    dev_id = f"LT-{digest}"
    try:
        id_file.parent.mkdir(parents=True, exist_ok=True)
        id_file.write_text(dev_id, encoding="utf-8")
    except Exception:
        pass
    return dev_id


def compute_canonical_sha256(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        payload or {},
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _request_json(
    method: str,
    endpoint: str,
    *,
    params: Optional[dict[str, Any]] = None,
    json_body: Optional[dict[str, Any]] = None,
    server_url: Optional[str] = None,
) -> ApiResult:
    base = (server_url or SERVER_URL).rstrip("/")
    if not base.startswith(("http://", "https://")):
        return ApiResult(False, 0, {}, "عنوان السيرفر غير صالح.")

    url = f"{base}{endpoint}"
    headers = {
        "Accept": "application/json",
        "User-Agent": f"LaderTareiq/{APP_VERSION} (Android; Flet)",
    }
    try:
        resp = requests.request(
            method=method.upper(),
            url=url,
            params=params,
            json=json_body,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        try:
            payload = resp.json()
            if not isinstance(payload, dict):
                payload = {"raw": payload}
        except ValueError:
            payload = {}

        msg = str(
            payload.get("message")
            or payload.get("detail")
            or f"استجابة غير متوقعة من السيرفر (HTTP {resp.status_code})."
        )
        ok = 200 <= resp.status_code < 300
        return ApiResult(ok, resp.status_code, payload, msg)
    except requests.Timeout:
        return ApiResult(False, 408, {}, "انتهت مهلة الاتصال بالسيرفر.")
    except requests.ConnectionError:
        return ApiResult(False, 503, {}, "تعذر الاتصال بالإنترنت أو بالسيرفر.")
    except requests.RequestException as ex:
        return ApiResult(False, 0, {}, f"خطأ في الشبكة: {ex}")


def check_health(server_url: Optional[str] = None) -> ApiResult:
    return _request_json("GET", "/api/health", server_url=server_url)


def fetch_app_config(server_url: Optional[str] = None) -> ApiResult:
    return _request_json("GET", "/api/app-config", server_url=server_url)


def fetch_ota_bundle(current_ota_version: Optional[str] = None, server_url: Optional[str] = None) -> ApiResult:
    st = load_state()
    ver = current_ota_version or st.get("ota_version") or OTA_VERSION
    res = _request_json("GET", "/api/ota-bundle", params={"ota_version": ver}, server_url=server_url)
    if not res.ok:
        return res

    data = res.data
    remote_ver = str(data.get("ota_version") or "").strip()
    payload = data.get("payload")
    expected_sha = str(data.get("sha256") or "").strip().lower()

    if not remote_ver or not isinstance(payload, dict):
        return ApiResult(False, res.status_code, data, "حزمة OTA غير مكتملة من السيرفر.")

    if expected_sha:
        actual_sha = compute_canonical_sha256(payload).lower()
        if actual_sha != expected_sha:
            return ApiResult(
                False,
                res.status_code,
                data,
                "فشل التحقق من سلامة حزمة OTA (تطابق SHA-256 غير صحيح).",
            )

    return ApiResult(True, res.status_code, data, "تم استلام حزمة OTA والتحقق منها بنجاح.")


def verify_license(
    license_key: str,
    *,
    device_id: Optional[str] = None,
    app_version: str = APP_VERSION,
    server_url: Optional[str] = None,
) -> ApiResult:
    clean_key = str(license_key or "").strip().upper()
    if not clean_key:
        return ApiResult(False, 400, {}, "يرجى إدخال كود التفعيل أولاً.")

    dev_id = (device_id or get_device_id()).strip()
    return _request_json(
        "POST",
        "/api/verify",
        json_body={
            "key": clean_key,
            "device_id": dev_id,
            "app_version": app_version,
        },
        server_url=server_url,
    )
