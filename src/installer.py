"""تحميل الحزم والتحقق من SHA-256 وفك الضغط بأمان لتطبيق Lader Tareiq."""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import requests

from config import APP_VERSION, DOWNLOAD_TIMEOUT, MAX_DOWNLOAD_BYTES


@dataclass
class InstallResult:
    ok: bool
    message: str
    output_path: str = ""


def _sanitize_filename(name: str, default_name: str = "patch_update.pak") -> str:
    cleaned = Path(str(name or "").strip()).name
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", cleaned)
    if not cleaned or cleaned in (".", ".."):
        return default_name
    return cleaned[:120]


def get_downloads_dir() -> Path:
    candidates: list[Path] = []
    for env_key in ("FLET_APP_STORAGE_DATA", "FLET_APP_STORAGE_TEMP"):
        val = os.environ.get(env_key)
        if val:
            candidates.append(Path(val) / "lader_tareiq_packages")
    candidates.append(Path.home() / ".lader_tareiq" / "packages")

    for target in candidates:
        try:
            target.mkdir(parents=True, exist_ok=True)
            test_file = target / ".write_test"
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink(missing_ok=True)
            return target
        except Exception:
            continue

    fallback = Path("/tmp/lader_tareiq_packages")
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def compute_file_sha256(file_path: Path) -> str:
    h = hashlib.sha256()
    with file_path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 64)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest().lower()


def download_and_prepare(
    url: str,
    *,
    file_name: str = "",
    expected_sha256: str = "",
    deploy_mode: str = "auto",
    on_progress: Optional[Callable[[float, str], None]] = None,
) -> InstallResult:
    clean_url = str(url or "").strip()
    if not clean_url.startswith(("http://", "https://")):
        return InstallResult(False, "رابط التحميل غير صالح.")

    target_name = _sanitize_filename(file_name, "patch_bundle.pak")
    out_dir = get_downloads_dir()
    temp_path = out_dir / f"{target_name}.part"
    final_path = out_dir / target_name

    if on_progress:
        on_progress(0.05, "جاري الاتصال بخادم التحميل...")

    try:
        headers = {"User-Agent": f"LaderTareiq/{APP_VERSION} (Installer)"}
        with requests.get(clean_url, stream=True, headers=headers, timeout=DOWNLOAD_TIMEOUT) as resp:
            resp.raise_for_status()
            total_header = resp.headers.get("Content-Length")
            total_bytes = int(total_header) if total_header and total_header.isdigit() else 0

            if total_bytes > MAX_DOWNLOAD_BYTES:
                return InstallResult(False, "حجم الملف يتجاوز الحد الأقصى المسموح.")

            downloaded = 0
            with temp_path.open("wb") as out_f:
                for chunk in resp.iter_content(chunk_size=65536):
                    if not chunk:
                        continue
                    downloaded += len(chunk)
                    if downloaded > MAX_DOWNLOAD_BYTES:
                        out_f.close()
                        temp_path.unlink(missing_ok=True)
                        return InstallResult(False, "تم إيقاف التحميل لتجاوز الحد المسموح.")
                    out_f.write(chunk)
                    if on_progress:
                        if total_bytes > 0:
                            frac = min(0.85, 0.05 + 0.80 * (downloaded / total_bytes))
                            mb_done = downloaded / (1024 * 1024)
                            mb_total = total_bytes / (1024 * 1024)
                            on_progress(frac, f"جاري التحميل: {mb_done:.1f} / {mb_total:.1f} MB")
                        else:
                            mb_done = downloaded / (1024 * 1024)
                            on_progress(0.45, f"جاري التحميل: {mb_done:.1f} MB")

        if not temp_path.exists() or temp_path.stat().st_size == 0:
            temp_path.unlink(missing_ok=True)
            return InstallResult(False, "الملف المحمّل فارغ أو غير مكتمل.")

        clean_sha = str(expected_sha256 or "").strip().lower()
        if clean_sha:
            if on_progress:
                on_progress(0.88, "جاري التحقق من بصمة SHA-256...")
            actual_sha = compute_file_sha256(temp_path)
            if actual_sha != clean_sha:
                temp_path.unlink(missing_ok=True)
                return InstallResult(
                    False,
                    "فشل التحقق من SHA-256: الملف تالف أو غير مطابق للبصمة المعتمدة.",
                )

        os.replace(temp_path, final_path)

        mode = str(deploy_mode or "auto").lower().strip()
        if final_path.suffix.lower() == ".zip" and mode in ("auto", "folder"):
            if on_progress:
                on_progress(0.94, "جاري فك ضغط الأرشيف بأمان...")
            extract_dir = out_dir / f"{final_path.stem}_extracted"
            if extract_dir.exists():
                shutil.rmtree(extract_dir, ignore_errors=True)
            extract_dir.mkdir(parents=True, exist_ok=True)

            resolved_root = extract_dir.resolve()
            with zipfile.ZipFile(final_path, "r") as zf:
                for member in zf.infolist():
                    member_path = (extract_dir / member.filename).resolve()
                    if not str(member_path).startswith(str(resolved_root) + os.sep) and member_path != resolved_root:
                        shutil.rmtree(extract_dir, ignore_errors=True)
                        return InstallResult(False, "تم رفض أرشيف يحتوي على مسارات غير آمنة.")
                zf.extractall(extract_dir)

            if on_progress:
                on_progress(1.0, "تم تجهيز الحزمة وفك الضغط بنجاح.")
            return InstallResult(
                True,
                f"تم التحميل والتجهيز بنجاح في: {extract_dir}",
                str(extract_dir),
            )

        if on_progress:
            on_progress(1.0, "تم تحميل الملف وتجهيزه بنجاح.")
        return InstallResult(
            True,
            f"تم تحميل الملف وحفظه في: {final_path}",
            str(final_path),
        )

    except requests.Timeout:
        temp_path.unlink(missing_ok=True)
        return InstallResult(False, "انتهت مهلة تحميل الملف.")
    except requests.RequestException as ex:
        temp_path.unlink(missing_ok=True)
        return InstallResult(False, f"تعذر تحميل الملف: {ex}")
    except zipfile.BadZipFile:
        temp_path.unlink(missing_ok=True)
        return InstallResult(False, "ملف ZIP تالف أو غير صالح.")
    except Exception as ex:
        temp_path.unlink(missing_ok=True)
        return InstallResult(False, f"حدث خطأ أثناء التجهيز: {ex}")
