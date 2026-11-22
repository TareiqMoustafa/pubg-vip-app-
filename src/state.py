"""إدارة حالة التطبيق وحفظ الإعدادات والسجل محلياً."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_STATE: dict[str, Any] = {
    "key": None,
    "installed_version": "",
    "deployed_name": "",
    "auto_update": False,
    "notifications_enabled": True,
    "ota_version": "1.0.0",
    "ota_payload": {},
    "log": [],
}


def _state_path() -> Path:
    base = Path(os.environ.get("FLET_APP_STORAGE_DATA") or Path.home())
    return base / "lader_tareiq_state.json"


def load() -> dict[str, Any]:
    """تحميل الحالة المحفوظة مع دمج القيم الافتراضية."""
    data = dict(DEFAULT_STATE)
    data["ota_payload"] = {}
    data["log"] = []
    path = _state_path()
    try:
        if path.exists():
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                for k, v in DEFAULT_STATE.items():
                    if k in raw and raw[k] is not None:
                        data[k] = raw[k]
                if not isinstance(data.get("ota_payload"), dict):
                    data["ota_payload"] = {}
                if not isinstance(data.get("log"), list):
                    data["log"] = []
    except (OSError, ValueError):
        pass
    return data


def save(**updates: Any) -> dict[str, Any]:
    """تحديث وحفظ حقول محددة في ملف الحالة. تمرير None يحذف/يعيد القيمة الافتراضية."""
    current = load()
    for k, v in updates.items():
        if v is None and k in DEFAULT_STATE:
            default_v = DEFAULT_STATE[k]
            current[k] = dict(default_v) if isinstance(default_v, dict) else (
                list(default_v) if isinstance(default_v, list) else default_v
            )
        else:
            current[k] = v

    path = _state_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)
    except OSError:
        pass
    return current


def add_log(kind: str, message: str, limit: int = 100) -> list[dict[str, str]]:
    """إضافة حدث جديد إلى سجل النشاط."""
    current = load()
    logs: list[dict[str, str]] = list(current.get("log") or [])
    logs.append(
        {
            "t": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "k": str(kind or "info"),
            "m": str(message or ""),
        }
    )
    if len(logs) > limit:
        logs = logs[-limit:]
    save(log=logs)
    return logs


def get_log() -> list[dict[str, str]]:
    """استرجاع سجل الأحداث."""
    logs = load().get("log")
    return logs if isinstance(logs, list) else []
