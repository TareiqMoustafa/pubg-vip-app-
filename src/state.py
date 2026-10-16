"""حفظ حالة التطبيق محلياً (الكود المحفوظ ورقم الباتش المثبّت) في ملف JSON داخل مجلد التطبيق."""
from __future__ import annotations

import json
import os
from pathlib import Path


def _path() -> Path:
    base = Path(os.environ.get("FLET_APP_STORAGE_DATA") or Path.home())
    return base / "state.json"


def load() -> dict:
    try:
        data = json.loads(_path().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save(**changes) -> None:
    data = load()
    for k, v in changes.items():
        if v is None:
            data.pop(k, None)
        else:
            data[k] = v
    try:
        p = _path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def add_log(kind: str, message: str) -> None:
    """سجل نشاط محلي (آخر 60 حدثاً)."""
    from datetime import datetime, timezone
    entries = load().get("log") or []
    entries.append({"t": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "k": kind, "m": message})
    save(log=entries[-60:])


def get_log() -> list:
    entries = load().get("log")
    return entries if isinstance(entries, list) else []
