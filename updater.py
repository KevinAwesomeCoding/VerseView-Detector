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


# ── Helpers ────────────────────────────────────────────────────────────────────

def _internal_dir() -> str:
    """Absolute path to the _internal folder (or source dir when running raw)."""
    if hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def _current_version() -> str:
    path = os.path.join(_internal_dir(), "version.txt")
    try:
        with open(path, encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
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
            "tag_name":     latest_tag,
            "asset_name":   name,
            "download_url": url,
            "release_url":  data.get("html_url", GITHUB_REL_PAGE),
            "is_windows":   sys.platform == "win32",
            "is_mac_intel": _is_mac_intel(),
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

            # ── 2. Windows — download .new.exe, write bat helper, signal restart ──
            if sys.platform == "win32":
                # Place the new exe next to the current one
                current_exe = sys.executable
                new_exe     = current_exe + ".new"

                # Rename the downloaded file to .new alongside the running exe
                shutil.move(tmp_path, new_exe)
                tmp_path = None  # prevent finally-block deletion

                # Write a .bat that waits for this process to exit, swaps files, relaunches
                bat_path = current_exe + ".updater.bat"
                pid      = os.getpid()
                bat = (
                    "@echo off\n"
                    f"echo Waiting for VerseView to close...\n"
                    f":wait\n"
                    f"tasklist /FI \"PID eq {pid}\" 2>NUL | find \"{pid}\" >NUL\n"
                    f"if not errorlevel 1 (timeout /t 1 /nobreak >NUL & goto wait)\n"
                    f"echo Applying update...\n"
                    f"del /F /Q \"{current_exe}\"\n"
                    f"rename \"{new_exe}\" \"{os.path.basename(current_exe)}\"\n"
                    f"start \"\" \"{current_exe}\"\n"
                    f"del /F /Q \"%~f0\"\n"  # bat deletes itself
                )
                with open(bat_path, "w", encoding="utf-8") as bf:
                    bf.write(bat)

                # Launch the bat detached (it runs after we exit)
                import subprocess
                subprocess.Popen(
                    ["cmd.exe", "/c", bat_path],
                    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                    close_fds=True,
                )

                if on_progress:
                    on_progress(100)
                if on_done:
                    on_done()   # GUI will call restart_app() → closes this process → bat takes over
                return

            if not zipfile.is_zipfile(tmp_path):
                raise ValueError("Downloaded file is not a valid zip archive.")

            # ── 3. Mac Intel — full _internal/ replacement ────────────────────
            if _is_mac_intel():
                entries_in_internal = [
                    e for e in zipfile.ZipFile(tmp_path).namelist()
                    if e.startswith(_INTEL_INTERNAL_PREFIX) and not e.endswith("/")
                ]

                if not entries_in_internal:
                    raise ValueError(
                        f"Could not find _internal/ contents in zip.\n"
                        f"Expected path prefix: {_INTEL_INTERNAL_PREFIX}"
                    )

                replaced = 0
                total_files = len(entries_in_internal)
                with zipfile.ZipFile(tmp_path, "r") as zf:
                    for i, entry in enumerate(entries_in_internal):
                        # Strip the zip prefix to get just the filename/subpath
                        rel = entry[len(_INTEL_INTERNAL_PREFIX):]
                        if not rel:
                            continue
                        dest = os.path.join(internal, rel)
                        # Create subdirectories if needed
                        os.makedirs(os.path.dirname(dest), exist_ok=True)
                        dest_tmp = dest + ".new"
                        with zf.open(entry) as src, open(dest_tmp, "wb") as dst:
                            shutil.copyfileobj(src, dst)
                        os.replace(dest_tmp, dest)
                        replaced += 1
                        if on_progress:
                            on_progress(82 + int(i / total_files * 16))

                logger.info(f"✅ Mac Intel full update: replaced {replaced} files in _internal/")

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


# update check again hehe