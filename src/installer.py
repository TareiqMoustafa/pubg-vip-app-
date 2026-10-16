"""تحميل الباتش ونقله إلى مجلد اللعبة.

طرق النقل بالترتيب:
  1) نسخ مباشر (يعمل على أندرويد 10 وما دون أو مع صلاحيات كاملة).
  2) rish (Shizuku) إن كان متاحاً للتطبيق.
  3) أمر نقل جاهز للنسخ يُنفَّذ في طرفية Shizuku (مثل aShell You).
الملف المؤقت يُحفظ في مجلد التطبيق على التخزين الخارجي ليستطيع Shizuku قراءته.
الحذف (إزالة الباتش) يستخدم نفس الطرق الثلاث.
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import re
import shlex
import shutil
import tempfile
import time
from dataclasses import dataclass, field
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


# ------------------------------------------------------------ هدف النقل (يحدده السيرفر)
FILE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,100}\.pak$")
_override_name = ""
_override_pkg = ""


def configure_target(file_name: str = "", game_package: str = "") -> None:
    """اسم الباتش وحزمة اللعبة يتغيران مع كل تحديث/منطقة؛ السيرفر يرسلهما بدون إعادة بناء التطبيق."""
    global _override_name, _override_pkg
    _override_name = file_name if FILE_RE.match(file_name or "") else ""
    _override_pkg = game_package if PKG_RE.match(game_package or "") else ""


def target_name() -> str:
    return _override_name or CFG.TARGET_FILE_NAME


def target_dir() -> str:
    if _override_pkg:
        return (f"/storage/emulated/0/Android/data/{_override_pkg}/files/UE4Game/"
                "ShadowTrackerExtra/ShadowTrackerExtra/Saved/Paks/")
    return CFG.TARGET_DIR


# ------------------------------------------------------------ مجلد التجهيز
STORAGE_ROOT = "/storage/emulated"


@dataclass
class Staging:
    path: Path
    shell_readable: bool          # هل يستطيع Shizuku/الشل قراءة هذا المجلد؟
    notes: list = field(default_factory=list)


last_staging: Optional[Staging] = None
# إحصاءات التحميل الحالي (للواجهة): البايتات المحمّلة والإجمالي والسرعة بالبايت/ثانية
progress_info: dict = {"done": 0, "total": 0, "speed": 0.0}


def _detect_app() -> tuple:
    """يستخرج (اسم الحزمة، رقم المستخدم) من مسار الكاش، وبديله cmdline."""
    uid, pkg = "0", None
    m = re.match(r"^/data/(?:user/(\d+)/|data/)([a-z][\w.]*)/", tempfile.gettempdir() + "/")
    if m:
        uid, pkg = m.group(1) or "0", m.group(2)
    if not pkg:
        try:
            name = Path("/proc/self/cmdline").read_bytes().split(b"\0")[0].decode()
        except OSError:
            name = ""
        if PKG_RE.match(name):
            pkg = name
    return pkg, uid


def _probe(d: Path) -> None:
    d.mkdir(parents=True, exist_ok=True)
    p = d / ".probe"
    p.write_bytes(b"1")
    p.unlink()


def staging_dir() -> Staging:
    """يختار مجلداً يكتب فيه التطبيق ويقرؤه Shizuku (المجلد الداخلي /data/... لا يقرؤه الشل)."""
    global last_staging
    pkg, uid = _detect_app()
    notes: list = []
    candidates: list = []
    if pkg:
        root = Path(f"{STORAGE_ROOT}/{uid}")
        candidates += [
            root / "Android" / "media" / pkg,
            root / "Android" / "data" / pkg / "files",
            root / "Download" / "PUBG_VIP",
        ]
    for d in candidates:
        try:
            _probe(d)
            last_staging = Staging(d, True, notes)
            return last_staging
        except OSError as ex:
            notes.append(f"{d}: {ex.__class__.__name__}")
    last_staging = Staging(Path(tempfile.gettempdir()), False, notes)
    return last_staging


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


async def _download_once(url: str, dest: Path, on_progress: ProgressCb, expected_sha: str = "") -> None:
    part = dest.with_suffix(dest.suffix + ".part")
    sha = hashlib.sha256()
    headers = {"User-Agent": CFG.USER_AGENT, "Accept": "*/*"}
    try:
        async with httpx.AsyncClient(timeout=CFG.DOWNLOAD_TIMEOUT, follow_redirects=True, headers=headers) as client:
            async with client.stream("GET", url) as r:
                r.raise_for_status()
                total = int(r.headers.get("content-length", 0))
                done = 0
                t0 = time.monotonic()
                progress_info.update(done=0, total=total, speed=0.0)
                with open(part, "wb") as f:
                    async for chunk in r.aiter_bytes(CFG.CHUNK_SIZE):
                        f.write(chunk)
                        sha.update(chunk)
                        done += len(chunk)
                        elapsed = max(time.monotonic() - t0, 0.001)
                        progress_info.update(done=done, total=total, speed=done / elapsed)
                        on_progress(done / total if total else None)
        if done == 0 or (total and done != total):
            raise InstallError("الملف المحمَّل ناقص أو فارغ.")
        want = (expected_sha or CFG.PATCH_SHA256 or "").strip().lower()
        if want and sha.hexdigest().lower() != want:
            raise InstallError("فشل التحقق من سلامة الملف (SHA-256).")
        os.replace(part, dest)
    except BaseException:
        part.unlink(missing_ok=True)
        raise


async def download_patch(on_progress: ProgressCb, url: str = "", sha256: str = "") -> Path:
    dest = staging_dir().path / target_name()
    errors: list[str] = []
    for src in _sources(url):
        for attempt in range(1, CFG.DOWNLOAD_RETRIES + 1):
            try:
                on_progress(None)
                await _download_once(src, dest, on_progress, sha256)
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
    target = f"{target_dir()}{target_name()}"
    return (
        f"mkdir -p {shlex.quote(target_dir())} && cp -f {shlex.quote(str(src))} {shlex.quote(target)}"
        f" && ls -l {shlex.quote(target)}"
    )


def _try_direct(src: Path) -> bool:
    try:
        Path(target_dir()).mkdir(parents=True, exist_ok=True)
        dst = Path(target_dir()) / target_name()
        shutil.copyfile(src, dst)
        return dst.stat().st_size == src.stat().st_size
    except OSError:
        return False


async def _try_rish(src: Path) -> bool:
    rish = shutil.which("rish") or os.environ.get("RISH_PATH")
    if not rish:
        return False
    target = f"{target_dir()}{target_name()}"
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


# ------------------------------------------------------------ حذف الباتش
def manual_remove_command() -> str:
    target = f"{target_dir()}{target_name()}"
    return f"rm -f {shlex.quote(target)} && ls -l {shlex.quote(target_dir())} | head -n 5"


def _try_direct_remove() -> bool:
    """True فقط إذا حُذف الملف فعلاً (FileNotFoundError قد يعني أن المجلد محجوب، فلا نعتبره نجاحاً)."""
    try:
        os.remove(Path(target_dir()) / target_name())
        return True
    except OSError:
        return False


async def _try_rish_remove() -> bool:
    rish = shutil.which("rish") or os.environ.get("RISH_PATH")
    if not rish:
        return False
    target = f"{target_dir()}{target_name()}"
    cmd = f"rm -f {shlex.quote(target)} && test ! -e {shlex.quote(target)}"
    try:
        proc = await asyncio.create_subprocess_exec(
            rish, "-c", cmd,
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
        )
        return await asyncio.wait_for(proc.wait(), timeout=60) == 0
    except (OSError, asyncio.TimeoutError):
        return False


async def remove_patch() -> InstallResult:
    """يحذف ملف الباتش من مجلد اللعبة؛ تعود اللعبة لملفاتها الأصلية (قد تنزّلها من جديد عند الفتح)."""
    if await asyncio.to_thread(_try_direct_remove):
        return InstallResult("direct")
    if await _try_rish_remove():
        return InstallResult("shizuku")
    raise InstallError(
        "الحذف التلقائي غير متاح على جهازك.",
        manual_command=manual_remove_command(),
    )


# ------------------------------------------------------------ فحص الجاهزية
def diagnostics() -> list:
    """قائمة (العنوان، الحالة ok|warn|info، التفصيل) لفحوصات الجهاز؛ لا تغيّر شيئاً على الجهاز."""
    out: list = []
    st = staging_dir()
    try:
        free = shutil.disk_usage(st.path).free / (1024 * 1024)
        out.append(("المساحة الحرة", "ok" if free >= 200 else "warn", f"{free:,.0f} MB"))
    except OSError:
        out.append(("المساحة الحرة", "info", "تعذر القياس"))
    out.append((
        "مجلد التجهيز", "ok" if st.shell_readable else "warn",
        "يقرؤه Shizuku" if st.shell_readable else "غير مرئي لـ Shizuku — فعّل «إدارة كل الملفات» للتطبيق",
    ))
    out.append((
        "Shizuku (rish)", "ok" if (shutil.which("rish") or os.environ.get("RISH_PATH")) else "info",
        "متاح للتطبيق" if (shutil.which("rish") or os.environ.get("RISH_PATH")) else "غير متاح — سيظهر أمر نقل يدوي",
    ))
    try:
        writable = os.access(target_dir(), os.W_OK)
        out.append(("الكتابة المباشرة لمجلد اللعبة", "ok" if writable else "info",
                    "مسموحة" if writable else "غير مسموحة (طبيعي على أندرويد 11+)"))
    except OSError:
        out.append(("الكتابة المباشرة لمجلد اللعبة", "info", "غير متاحة"))
    try:
        exists = os.path.isdir(target_dir())
        out.append(("مجلد اللعبة", "ok" if exists else "info",
                    "ظاهر للتطبيق" if exists else "غير ظاهر للتطبيق (لا يعني أن اللعبة غير مثبّتة)"))
    except OSError:
        out.append(("مجلد اللعبة", "info", "غير ظاهر للتطبيق"))
    return out


def cleanup(path: Optional[Path] = None) -> None:
    if path is None:
        return
    for p in (path, path.with_suffix(path.suffix + ".part")):
        try:
            p.unlink(missing_ok=True)
        except OSError:
            pass
