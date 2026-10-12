"""تحميل الباتش ونقله إلى مجلد اللعبة.

طرق النقل بالترتيب:
  1) نسخ مباشر (يعمل على أندرويد 10 وما دون أو مع صلاحيات كاملة).
  2) rish (Shizuku) إن كان متاحاً للتطبيق.
  3) أمر نقل جاهز للنسخ يُنفَّذ في طرفية Shizuku (مثل aShell You).
الملف المؤقت يُحفظ في مجلد التطبيق على التخزين الخارجي ليستطيع Shizuku قراءته.
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import re
import shlex
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import httpx

from config import CFG

ProgressCb = Callable[[Optional[float]], None]
PKG_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z0-9_]+)+$")


class InstallError(Exception):
    def __init__(self, message: str, manual_command: str = "", staged: Optional[Path] = None):
        super().__init__(message)
        self.manual_command = manual_command
        self.staged = staged


@dataclass
class InstallResult:
    method: str  # "direct" | "shizuku"


# ------------------------------------------------------------ مجلد التجهيز
def _package_name() -> Optional[str]:
    try:
        name = Path("/proc/self/cmdline").read_bytes().split(b"\0")[0].decode()
    except OSError:
        return None
    return name if PKG_RE.match(name) and Path("/storage/emulated/0/Android").exists() else None


def staging_dir() -> Path:
    candidates = []
    pkg = _package_name()
    if pkg:  # مجلد التطبيق الخارجي: لا يحتاج صلاحية، ويقرأه Shizuku
        candidates.append(Path(f"/storage/emulated/0/Android/data/{pkg}/files"))
    candidates.append(Path(tempfile.gettempdir()))
    for d in candidates:
        try:
            d.mkdir(parents=True, exist_ok=True)
            probe = d / ".probe"
            probe.write_bytes(b"1")
            probe.unlink()
            return d
        except OSError:
            continue
    return Path(tempfile.gettempdir())


# ------------------------------------------------------------ التحميل
def _explain(ex: Exception) -> str:
    if isinstance(ex, httpx.RemoteProtocolError):
        return "السيرفر قطع الاتصال (الرابط محجوب أو الملف محذوف)"
    if isinstance(ex, httpx.HTTPStatusError):
        return f"الرابط رد بخطأ {ex.response.status_code}"
    if isinstance(ex, httpx.TimeoutException):
        return "انتهت مهلة الاتصال"
    if isinstance(ex, httpx.ConnectError):
        return "تعذر الاتصال بالرابط"
    return str(ex) or ex.__class__.__name__


def _sources(preferred: str) -> list[str]:
    out: list[str] = []
    for u in (preferred, CFG.PATCH_DOWNLOAD_URL, *CFG.PATCH_MIRRORS):
        if u and u not in out:
            out.append(u)
    return out


async def _download_once(url: str, dest: Path, on_progress: ProgressCb) -> None:
    part = dest.with_suffix(dest.suffix + ".part")
    sha = hashlib.sha256()
    headers = {"User-Agent": CFG.USER_AGENT, "Accept": "*/*"}
    try:
        async with httpx.AsyncClient(timeout=CFG.DOWNLOAD_TIMEOUT, follow_redirects=True, headers=headers) as client:
            async with client.stream("GET", url) as r:
                r.raise_for_status()
                total = int(r.headers.get("content-length", 0))
                done = 0
                with open(part, "wb") as f:
                    async for chunk in r.aiter_bytes(CFG.CHUNK_SIZE):
                        f.write(chunk)
                        sha.update(chunk)
                        done += len(chunk)
                        on_progress(done / total if total else None)
        if done == 0 or (total and done != total):
            raise InstallError("الملف المحمَّل ناقص أو فارغ.")
        if CFG.PATCH_SHA256 and sha.hexdigest().lower() != CFG.PATCH_SHA256.lower():
            raise InstallError("فشل التحقق من سلامة الملف (SHA-256).")
        os.replace(part, dest)
    except BaseException:
        part.unlink(missing_ok=True)
        raise


async def download_patch(on_progress: ProgressCb, url: str = "") -> Path:
    dest = staging_dir() / CFG.TARGET_FILE_NAME
    errors: list[str] = []
    for src in _sources(url):
        for attempt in range(1, CFG.DOWNLOAD_RETRIES + 1):
            try:
                on_progress(None)
                await _download_once(src, dest, on_progress)
                return dest
            except InstallError:
                raise
            except httpx.HTTPStatusError as ex:
                errors.append(_explain(ex))
                break  # 4xx/5xx: لا فائدة من إعادة نفس الرابط
            except (httpx.HTTPError, OSError) as ex:
                errors.append(_explain(ex))
                if attempt < CFG.DOWNLOAD_RETRIES:
                    await asyncio.sleep(2 * attempt)
    raise InstallError("فشل التحميل: " + (errors[-1] if errors else "سبب غير معروف"))


# ------------------------------------------------------------ النقل
def manual_command(src: Path) -> str:
    target = f"{CFG.TARGET_DIR}{CFG.TARGET_FILE_NAME}"
    return f"mkdir -p {shlex.quote(CFG.TARGET_DIR)} && cp -f {shlex.quote(str(src))} {shlex.quote(target)}"


def _try_direct(src: Path) -> bool:
    try:
        Path(CFG.TARGET_DIR).mkdir(parents=True, exist_ok=True)
        dst = Path(CFG.TARGET_DIR) / CFG.TARGET_FILE_NAME
        shutil.copyfile(src, dst)
        return dst.stat().st_size == src.stat().st_size
    except OSError:
        return False


async def _try_rish(src: Path) -> bool:
    rish = shutil.which("rish") or os.environ.get("RISH_PATH")
    if not rish:
        return False
    target = f"{CFG.TARGET_DIR}{CFG.TARGET_FILE_NAME}"
    cmd = f"{manual_command(src)} && test -s {shlex.quote(target)}"
    try:
        proc = await asyncio.create_subprocess_exec(
            rish, "-c", cmd,
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
        )
        return await asyncio.wait_for(proc.wait(), timeout=60) == 0
    except (OSError, asyncio.TimeoutError):
        return False


async def install_patch(src: Path) -> InstallResult:
    if await asyncio.to_thread(_try_direct, src):
        return InstallResult("direct")
    if await _try_rish(src):
        return InstallResult("shizuku")
    raise InstallError(
        "تم التحميل، لكن النقل التلقائي غير متاح على جهازك.",
        manual_command=manual_command(src),
        staged=src,
    )


def cleanup(path: Optional[Path] = None) -> None:
    if path is None:
        return
    for p in (path, path.with_suffix(path.suffix + ".part")):
        try:
            p.unlink(missing_ok=True)
        except OSError:
            pass
