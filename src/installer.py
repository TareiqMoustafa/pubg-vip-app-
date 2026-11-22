"""تحميل الباتش أو المجلد ونقله مع دعم الأذونات والنسخ الاحتياطي والاستعادة."""
from __future__ import annotations

import asyncio
import hashlib
import os
import re
import shlex
import shutil
import tempfile
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import httpx

from config import CFG

ProgressCb = Callable[[Optional[float]], None]
PKG_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z0-9_]+)+$")
FILE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,120}\.pak$")
ZIP_RE = re.compile(r"\.(zip)$", re.IGNORECASE)
STORAGE_ROOT = "/storage/emulated"


class InstallError(Exception):
    def __init__(self, message: str, manual_command: str = "", staged: Optional[Path] = None):
        super().__init__(message)
        self.manual_command = manual_command
        self.staged = staged


@dataclass
class InstallResult:
    method: str  # "direct" | "shizuku"
    deployed_name: str = ""
    kind: str = "pak"  # "pak" | "folder"


@dataclass
class Staging:
    path: Path
    shell_readable: bool
    notes: list = field(default_factory=list)


_override_name = ""
_override_pkg = ""
last_staging: Optional[Staging] = None
progress_info: dict = {"done": 0, "total": 0, "speed": 0.0}


def configure_target(file_name: str = "", game_package: str = "") -> None:
    global _override_name, _override_pkg
    _override_name = file_name if FILE_RE.match(file_name or "") else ""
    _override_pkg = game_package if PKG_RE.match(game_package or "") else ""


def target_name() -> str:
    return _override_name or CFG.TARGET_FILE_NAME


def target_dir() -> str:
    if _override_pkg:
        return (
            f"/storage/emulated/0/Android/data/{_override_pkg}/files/UE4Game/"
            "ShadowTrackerExtra/ShadowTrackerExtra/Saved/Paks/"
        )
    return CFG.TARGET_DIR


def is_deployed_present(deployed_name: str = "") -> bool:
    name = deployed_name or target_name()
    try:
        return (Path(target_dir()) / name).exists()
    except OSError:
        return False


def has_rish() -> bool:
    return bool(shutil.which("rish") or os.environ.get("RISH_PATH"))


def _backup_dir() -> Path:
    base = Path(os.environ.get("FLET_APP_STORAGE_DATA") or Path.home())
    return base / "backups"


def _detect_app() -> tuple[Optional[str], str]:
    uid, pkg = "0", None
    m = re.match(r"^/data/(?:user/(\d+)/|data/)([a-z][\w.]*)/", tempfile.gettempdir() + "/")
    if m:
        uid, pkg = m.group(1) or "0", m.group(2)
    if not pkg:
        try:
            name = Path("/proc/self/cmdline").read_bytes().split(b"\0")[0].decode(errors="ignore")
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
    global last_staging
    pkg, uid = _detect_app()
    notes: list[str] = []
    candidates: list[Path] = []
    if pkg:
        root = Path(f"{STORAGE_ROOT}/{uid}")
        candidates += [
            root / "Android" / "media" / pkg,
            root / "Android" / "data" / pkg / "files",
            root / "Download" / "LaderTareiq",
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
                total = int(r.headers.get("content-length") or 0)
                done = 0
                t0 = time.monotonic()
                progress_info.update(done=0, total=total, speed=0.0)
                with open(part, "wb") as f:
                    async for chunk in r.aiter_bytes(CFG.CHUNK_SIZE):
                        if not chunk:
                            continue
                        f.write(chunk)
                        sha.update(chunk)
                        done += len(chunk)
                        elapsed = max(time.monotonic() - t0, 0.001)
                        progress_info.update(done=done, total=total, speed=done / elapsed)
                        on_progress(done / total if total > 0 else None)
        if done == 0 or (total > 0 and done != total):
            raise InstallError("الملف المحمَّل ناقص أو فارغ.")
        want = (expected_sha or CFG.PATCH_SHA256 or "").strip().lower()
        if want and sha.hexdigest().lower() != want:
            raise InstallError("فشل التحقق من سلامة الملف (SHA-256).")
        dest.parent.mkdir(parents=True, exist_ok=True)
        os.replace(part, dest)
    except BaseException:
        part.unlink(missing_ok=True)
        raise


async def download_patch(
    on_progress: ProgressCb,
    url: str = "",
    sha256: str = "",
    deploy_mode: str = "auto",
) -> Path:
    mode = (deploy_mode or "auto").lower()
    is_archive = mode == "folder" or bool(ZIP_RE.search(url or ""))
    fname = f"{CFG.FALLBACK_FOLDER_NAME}.zip" if is_archive else target_name()
    dest = staging_dir().path / fname
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
                break
            except (httpx.HTTPError, OSError) as ex:
                errors.append(_explain(ex))
                if attempt < CFG.DOWNLOAD_RETRIES:
                    await asyncio.sleep(2 * attempt)
    raise InstallError("فشل التحميل: " + (errors[-1] if errors else "سبب غير معروف"))


def _extract_archive(archive_path: Path) -> Path:
    extract_root = archive_path.parent / f"_unpacked_{archive_path.stem}"
    if extract_root.exists():
        shutil.rmtree(extract_root, ignore_errors=True)
    extract_root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, "r") as zf:
        for member in zf.infolist():
            member_path = (extract_root / member.filename).resolve()
            if not str(member_path).startswith(str(extract_root.resolve())):
                raise InstallError("الأرشيف يحتوي على مسار غير آمن.")
        zf.extractall(extract_root)
    entries = [p for p in extract_root.iterdir() if not p.name.startswith("__MACOSX")]
    if len(entries) == 1 and entries[0].is_dir():
        return entries[0]
    folder_dst = archive_path.parent / CFG.FALLBACK_FOLDER_NAME
    if folder_dst.exists():
        shutil.rmtree(folder_dst, ignore_errors=True)
    shutil.move(str(extract_root), str(folder_dst))
    return folder_dst


def _backup_existing(dst_path: Path) -> None:
    if not dst_path.exists():
        return
    try:
        bdir = _backup_dir()
        bdir.mkdir(parents=True, exist_ok=True)
        btarget = bdir / dst_path.name
        if btarget.exists():
            if btarget.is_dir():
                shutil.rmtree(btarget, ignore_errors=True)
            else:
                btarget.unlink(missing_ok=True)
        if dst_path.is_dir():
            shutil.copytree(dst_path, btarget)
        else:
            shutil.copy2(dst_path, btarget)
    except OSError:
        pass


def manual_command(src: Path, kind: str = "pak", deployed_name: str = "") -> str:
    dst_dir = target_dir()
    name = deployed_name or (src.name if kind == "folder" else target_name())
    target = f"{dst_dir}{name}"
    if kind == "folder":
        return (
            f"mkdir -p {shlex.quote(target)} && cp -rf {shlex.quote(str(src))}/. {shlex.quote(target)}/"
            f" && ls -la {shlex.quote(target)}"
        )
    return (
        f"mkdir -p {shlex.quote(dst_dir)} && cp -f {shlex.quote(str(src))} {shlex.quote(target)}"
        f" && ls -l {shlex.quote(target)}"
    )


def _try_direct_copy(src: Path, kind: str, deployed_name: str) -> bool:
    try:
        dst_root = Path(target_dir())
        dst_root.mkdir(parents=True, exist_ok=True)
        dst = dst_root / deployed_name
        _backup_existing(dst)
        if kind == "folder":
            if dst.exists():
                shutil.rmtree(dst, ignore_errors=True)
            shutil.copytree(src, dst)
            return dst.is_dir()
        shutil.copyfile(src, dst)
        return dst.is_file() and dst.stat().st_size == src.stat().st_size
    except OSError:
        return False


async def _try_rish_cmd(cmd: str) -> bool:
    rish = shutil.which("rish") or os.environ.get("RISH_PATH")
    if not rish:
        return False
    try:
        proc = await asyncio.create_subprocess_exec(
            rish, "-c", cmd,
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
        )
        return await asyncio.wait_for(proc.wait(), timeout=60) == 0
    except (OSError, asyncio.TimeoutError):
        return False


async def install_patch(src: Path) -> InstallResult:
    if zipfile.is_zipfile(src):
        payload_dir = await asyncio.to_thread(_extract_archive, src)
        kind = "folder"
        dname = payload_dir.name
        payload_src = payload_dir
    else:
        kind = "pak"
        dname = target_name()
        payload_src = src

    if await asyncio.to_thread(_try_direct_copy, payload_src, kind, dname):
        return InstallResult("direct", deployed_name=dname, kind=kind)

    target = f"{target_dir()}{dname}"
    cmd = f"{manual_command(payload_src, kind, dname)} && test -e {shlex.quote(target)}"
    if await _try_rish_cmd(cmd):
        return InstallResult("shizuku", deployed_name=dname, kind=kind)

    raise InstallError(
        "تم التحميل، لكن النقل التلقائي غير متاح على جهازك.",
        manual_command=manual_command(payload_src, kind, dname),
        staged=src,
    )


def manual_remove_command(deployed_name: str = "") -> str:
    name = deployed_name or target_name()
    target = f"{target_dir()}{name}"
    return f"rm -rf {shlex.quote(target)} && ls -la {shlex.quote(target_dir())} | head -n 8"


def _try_direct_remove(name: str) -> bool:
    dst = Path(target_dir()) / name
    try:
        if dst.is_symlink() or dst.is_file():
            dst.unlink()
            return True
        if dst.is_dir():
            shutil.rmtree(dst)
            return True
        return False
    except OSError:
        return False


async def remove_patch(deployed_name: str = "") -> InstallResult:
    name = deployed_name or target_name()
    if await asyncio.to_thread(_try_direct_remove, name):
        return InstallResult("direct", deployed_name=name, kind="pak")
    target = f"{target_dir()}{name}"
    cmd = f"rm -rf {shlex.quote(target)} && test ! -e {shlex.quote(target)}"
    if await _try_rish_cmd(cmd):
        return InstallResult("shizuku", deployed_name=name, kind="pak")
    raise InstallError(
        "الحذف التلقائي غير متاح على جهازك.",
        manual_command=manual_remove_command(name),
    )


async def restore_backup(deployed_name: str = "") -> InstallResult:
    bdir = _backup_dir()
    name = deployed_name or target_name()
    candidates = [bdir / name] if name else []
    if bdir.exists():
        candidates += [p for p in bdir.iterdir() if p not in candidates]
    src = next((p for p in candidates if p.exists()), None)
    if src is None:
        raise InstallError("لا توجد نسخة احتياطية محفوظة للاستعادة.")
    kind = "folder" if src.is_dir() else "pak"
    if await asyncio.to_thread(_try_direct_copy, src, kind, src.name):
        return InstallResult("direct", deployed_name=src.name, kind=kind)
    cmd = f"{manual_command(src, kind, src.name)} && test -e {shlex.quote(target_dir() + src.name)}"
    if await _try_rish_cmd(cmd):
        return InstallResult("shizuku", deployed_name=src.name, kind=kind)
    raise InstallError(
        "تعذر استعادة النسخة الاحتياطية تلقائياً.",
        manual_command=manual_command(src, kind, src.name),
    )


def diagnostics() -> list:
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
        "Shizuku (rish)", "ok" if has_rish() else "info",
        "متاح ومتصل للتطبيق" if has_rish() else "غير متاح — سيظهر أمر نقل يدوي أو عبر Shizuku",
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
    unpacked = path.parent / f"_unpacked_{path.stem}"
    if unpacked.exists():
        shutil.rmtree(unpacked, ignore_errors=True)
