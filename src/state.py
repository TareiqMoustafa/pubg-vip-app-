"""إدارة الحالة المحلية وسجل العمليات لتطبيق Lader Tareiq."""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LOCK = threading.Lock()

DEFAULT_STATE: dict[str, Any] = {
    "license_key": "",
    "license_status": "inactive",
    "license_message": "لم يتم تفعيل ترخيص بعد.",
    "license_type": "",
    "expires_at": "",
    "remaining_days": 0,
    "remaining_hours": 0,
    "total_days": 0,
    "installed_patch_version": "",
    "latest_patch_version": "",
    "download_url": "",
    "target_file_name": "",
    "game_package": "",
    "deploy_mode": "auto",
    "patch_sha256": "",
    "patch_notes": "",
    "force_patch_update": False,
    "ota_version": "1.0.0",
    "ota_payload": {},
    "latest_app_version": "",
    "update_url": "",
    "update_message": "",
    "notice": "",
    "support_url": "",
    "maintenance": False,
    "auto_update": False,
    "notifications_enabled": True,
    "last_synced_at": "",
    "logs": [],
}


def _storage_dir() -> Path:
    for env_key in ("FLET_APP_STORAGE_DATA", "FLET_APP_STORAGE_TEMP"):
        val = os.environ.get(env_key)
        if val:
            p = Path(val)
            try:
                p.mkdir(parents=True, exist_ok=True)
                return p
            except Exception:
                pass
    fallback = Path("/tmp/lader_tareiq_state")
    try:
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback
    except Exception:
        return Path(".")


def _state_file() -> Path:
    return _storage_dir() / "state.json"


def _clone_defaults() -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in DEFAULT_STATE.items():
        if isinstance(v, dict):
            out[k] = dict(v)
        elif isinstance(v, list):
            out[k] = list(v)
        else:
            out[k] = v
    return out


def load() -> dict[str, Any]:
    with _LOCK:
        data = _clone_defaults()
        path = _state_file()
        try:
            if path.exists():
                raw = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    for k, default_val in DEFAULT_STATE.items():
                        if k in raw and raw[k] is not None:
                            val = raw[k]
                            if isinstance(default_val, dict) and not isinstance(val, dict):
                                continue
                            if isinstance(default_val, list) and not isinstance(val, list):
                                continue
                            data[k] = val
        except Exception:
            pass
        return data


def save(**updates: Any) -> dict[str, Any]:
    with _LOCK:
        current = _clone_defaults()
        path = _state_file()
        try:
            if path.exists():
                raw = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    for k, default_val in DEFAULT_STATE.items():
                        if k in raw and raw[k] is not None:
                            current[k] = raw[k]
        except Exception:
            pass

        for k, v in updates.items():
            if k not in DEFAULT_STATE:
                continue
            if v is None:
                default_val = DEFAULT_STATE[k]
                current[k] = dict(default_val) if isinstance(default_val, dict) else (
                    list(default_val) if isinstance(default_val, list) else default_val
                )
            else:
                current[k] = v

        try:
            tmp_path = path.with_suffix(".tmp")
            tmp_path.write_text(
                json.dumps(current, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            os.replace(tmp_path, path)
        except Exception:
            try:
                path.write_text(
                    json.dumps(current, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            except Exception:
                pass
        return current


def add_log(kind: str, message: str, limit: int = 120) -> list[dict[str, str]]:
    current = load()
    logs: list[dict[str, str]] = list(current.get("logs") or [])
    logs.append(
        {
            "time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "kind": str(kind or "info").lower(),
            "message": str(message or "").strip(),
        }
    )
    if len(logs) > limit:
        logs = logs[-limit:]
    save(logs=logs)
    return logs


def clear_logs() -> None:
    save(logs=[])
