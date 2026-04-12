"""
updater.py — VerseView self-update module

Platform behaviour:
  Mac Intel  (x86_64) -> downloads VerseView-Detector-Mac-Intel.zip
                          replaces the ENTIRE _internal/ folder
                          (handles new libraries, not just Python files)
  Mac Silicon (arm64) -> downloads VerseView-Detector-Mac-Silicon-App.zip
                          replaces updatable Python files only
  Windows             -> opens browser to release page
                          (cannot replace a running .exe in-place)
"""

import sys
import os
import platform
import logging
import threading
import zipfile
import shutil
import tempfile

import requests
import certifi

logger = logging.getLogger(__name__)

REPO             = "KevinAwesomeCoding/VerseView-Detector"
GITHUB_API       = f"https://api.github.com/repos/{REPO}/releases/latest"
GITHUB_REL_PAGE  = f"https://github.com/{REPO}/releases/latest"

# Python files to hot-swap on Mac Silicon / fallback
UPDATABLE_FILES = {
    "vv_gui.py",
    "vv_streaming_master.py",
    "bible_fetcher.py",
    "parse_reference_eng.py",
    "parse_reference_hindi.py",
    "parse_reference_ml.py",
    "settings.py",
    "updater.py",
    "version.txt",
}

# Zip path prefix for Mac Intel _internal/ contents
_INTEL_INTERNAL_PREFIX = "VerseView-Mac-Intel-Release/VerseView Detector (Raw Executable)/_internal/"

# Zip path for the Mac Intel raw executable itself (vv_gui.py is compiled into it)
_INTEL_EXE_ZIP_PATH   = "VerseView-Mac-Intel-Release/VerseView Detector (Raw Executable)/VerseView Detector"

# Name of the raw executable on disk (same as sys.executable basename)
_INTEL_EXE_NAME       = "VerseView Detector"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _internal_dir() -> str:
    """Absolute path to the _internal folder (or source dir when running raw)."""
    if hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def _exe_dir() -> str:
    """Directory that contains the running executable (one level above _internal on Mac)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def _current_version() -> str:
    # On Mac Intel the updater also writes version.txt next to the exe (step 3c).
    # Check that location first so a fresh restart always sees the correct new tag.
    candidates = []
    if _is_mac_intel() and getattr(sys, "frozen", False):
        candidates.append(os.path.join(_exe_dir(), "version.txt"))
    candidates.append(os.path.join(_internal_dir(), "version.txt"))

    for path in candidates:
        try:
            with open(path, encoding="utf-8") as f:
                v = f.read().strip()
            if v:
                return v
        except Exception:
            continue
    return ""


def _run_number(tag: str) -> int:
    """Extract numeric run number from tag like 'build-abc1234-42' -> 42."""
    try:
        return int(tag.rsplit("-", 1)[-1])
    except Exception:
        return 0


def _is_mac_intel() -> bool:
    return sys.platform == "darwin" and platform.machine().lower() == "x86_64"


def _asset_name() -> str | None:
    if sys.platform == "win32":
        return "VerseView_Detector.exe"
    if sys.platform == "darwin":
        if _is_mac_intel():
            return "VerseView-Detector-Mac-Intel.zip"
        else:
            return "VerseView-Detector-Mac-Silicon-App.zip"
    return None


# ── Public API ─────────────────────────────────────────────────────────────────

def check_for_update() -> dict | None:
    """
    Returns a dict if a newer release is available, else None.
    Keys: tag_name, asset_name, download_url, release_url, is_windows
    """
    try:
        r = requests.get(
            GITHUB_API, timeout=8, verify=certifi.where(),
            headers={"Accept": "application/vnd.github+json"}
        )
        if r.status_code != 200:
            return None
        data       = r.json()
        latest_tag = data.get("tag_name", "")
        current    = _current_version()

        if not latest_tag:
            return None
        if _run_number(latest_tag) <= _run_number(current):
            return None  # already on latest

        name = _asset_name()
        url  = None
        for asset in data.get("assets", []):
            if asset["name"] == name:
                url = asset["browser_download_url"]
                break

        return {
            "tag_name":      latest_tag,
            "asset_name":    name,
            "download_url":  url,
            "release_url":   data.get("html_url", GITHUB_REL_PAGE),
            "release_notes": data.get("body", "").strip(),
            "is_windows":    sys.platform == "win32",
            "is_mac_intel":  _is_mac_intel(),
        }
    except Exception as e:
        logger.debug(f"Update check failed: {e}")
        return None


def download_and_apply(
    download_url: str,
    on_progress=None,   # callback(pct: int)  0-100
    on_done=None,       # callback()
    on_error=None,      # callback(msg: str)
):
    """
    Download the release asset and apply it. Runs in a daemon thread.

    Mac Intel  → full _internal/ replacement from the zip
    Mac Silicon → Python files only
    Windows    → open browser
    """
    def _run():
        tmp_path = None
        try:
            internal = _internal_dir()

            # ── 1. Download ───────────────────────────────────────────────────
            tmp_fd, tmp_path = tempfile.mkstemp(suffix=".vvupdate")
            os.close(tmp_fd)

            resp = requests.get(
                download_url, stream=True, timeout=120, verify=certifi.where()
            )
            resp.raise_for_status()
            total      = int(resp.headers.get("content-length", 0))
            downloaded = 0
            with open(tmp_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total and on_progress:
                            on_progress(int(downloaded / total * 80))

            if on_progress:
                on_progress(82)

            # ── 2. Windows — open releases page in browser ────────────────────
            if sys.platform == "win32":
                import webbrowser
                webbrowser.open(GITHUB_REL_PAGE)
                if on_progress:
                    on_progress(100)
                if on_done:
                    on_done()
                return

            if not zipfile.is_zipfile(tmp_path):
                raise ValueError("Downloaded file is not a valid zip archive.")

            # ── 3. Mac Intel — atomic whole _internal/ folder swap ────────────
            # Extract the new _internal/ from the zip into _internal.new/ sibling,
            # then do an atomic rename swap so the old folder is never half-deleted.
            if _is_mac_intel():
                with zipfile.ZipFile(tmp_path, "r") as zf:
                    all_names = zf.namelist()

                entries_in_internal = [
                    e for e in all_names
                    if e.startswith(_INTEL_INTERNAL_PREFIX) and not e.endswith("/")
                ]

                if not entries_in_internal:
                    raise ValueError(
                        f"Could not find _internal/ contents in zip.\n"
                        f"Expected path prefix: {_INTEL_INTERNAL_PREFIX}"
                    )

                exe_dir      = _exe_dir()
                internal     = _internal_dir()          # .../VerseView Detector (Raw Executable)/_internal
                new_internal = internal + ".new"        # staging dir
                old_internal = internal + ".old"        # backup dir

                # Clean up any leftovers from a previous failed/interrupted update
                if os.path.exists(new_internal):
                    shutil.rmtree(new_internal, ignore_errors=True)
                if os.path.exists(old_internal):
                    shutil.rmtree(old_internal, ignore_errors=True)

                total_files = len(entries_in_internal) + 1  # +1 for the exe

                # ── 3a. Extract entire new _internal/ into _internal.new/ ────
                with zipfile.ZipFile(tmp_path, "r") as zf:
                    for i, entry in enumerate(entries_in_internal):
                        rel = entry[len(_INTEL_INTERNAL_PREFIX):]
                        if not rel:
                            continue
                        dest = os.path.join(new_internal, rel)
                        os.makedirs(os.path.dirname(dest), exist_ok=True)
                        with zf.open(entry) as src, open(dest, "wb") as dst:
                            shutil.copyfileobj(src, dst)
                        if on_progress:
                            on_progress(82 + int(i / total_files * 10))

                    # ── 3b. Replace the raw executable (vv_gui.py is compiled in) ──
                    if _INTEL_EXE_ZIP_PATH in all_names:
                        dest_exe     = os.path.join(exe_dir, _INTEL_EXE_NAME)
                        dest_exe_tmp = dest_exe + ".new"
                        with zf.open(_INTEL_EXE_ZIP_PATH) as src, \
                             open(dest_exe_tmp, "wb") as dst:
                            shutil.copyfileobj(src, dst)
                        import stat
                        os.chmod(dest_exe_tmp,
                                 os.stat(dest_exe_tmp).st_mode
                                 | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                        os.replace(dest_exe_tmp, dest_exe)
                        logger.info(f"✅ Mac Intel: replaced executable '{_INTEL_EXE_NAME}'")
                    else:
                        logger.warning(
                            f"⚠️  Mac Intel: executable not found in zip at "
                            f"'{_INTEL_EXE_ZIP_PATH}'"
                        )

                    # ── 3c. Also write version.txt next to the exe ───────────
                    ver_zip_path = _INTEL_INTERNAL_PREFIX + "version.txt"
                    if ver_zip_path in all_names:
                        ver_dest = os.path.join(exe_dir, "version.txt")
                        ver_tmp  = ver_dest + ".new"
                        with zf.open(ver_zip_path) as src, open(ver_tmp, "wb") as dst:
                            shutil.copyfileobj(src, dst)
                        os.replace(ver_tmp, ver_dest)

                if on_progress:
                    on_progress(93)

                # ── 3d. Atomic swap: _internal → _internal.old, .new → _internal ──
                # os.rename is atomic on the same filesystem (APFS/HFS+).
                # If the rename fails we still have the new copy in .new so we can retry.
                os.rename(internal, old_internal)       # current → .old  (instant)
                os.rename(new_internal, internal)       # .new    → current (instant)
                shutil.rmtree(old_internal, ignore_errors=True)  # delete old

                if on_progress:
                    on_progress(96)

                logger.info(
                    f"✅ Mac Intel full update: swapped _internal/ "
                    f"({len(entries_in_internal)} files) + executable"
                )

            # ── 4. Mac Silicon — Python files only ────────────────────────────
            else:
                replaced = 0
                with zipfile.ZipFile(tmp_path, "r") as zf:
                    for entry in zf.namelist():
                        fname = os.path.basename(entry)
                        if fname in UPDATABLE_FILES and fname:
                            dest     = os.path.join(internal, fname)
                            dest_tmp = dest + ".new"
                            with zf.open(entry) as src, open(dest_tmp, "wb") as dst:
                                shutil.copyfileobj(src, dst)
                            os.replace(dest_tmp, dest)
                            replaced += 1

                if not replaced:
                    raise ValueError("No updatable Python files found in the archive.")

                logger.info(f"✅ Mac Silicon update: replaced {replaced} Python files")

            if on_progress:
                on_progress(100)
            if on_done:
                on_done()

        except Exception as e:
            logger.error(f"Update failed: {e}")
            if on_error:
                on_error(str(e))
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

    threading.Thread(target=_run, daemon=True).start()


def restart_app():
    """Relaunch the current process so updated files take effect."""
    try:
        os.execv(sys.executable, [sys.executable] + sys.argv)
    except Exception:
        import subprocess
        subprocess.Popen([sys.executable] + sys.argv)
        sys.exit(0)
