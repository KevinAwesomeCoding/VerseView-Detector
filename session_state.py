# session_state.py  —  VerseView session persistence
# Saves to the same user-data directory as settings.py.
# No API keys are ever written here — sermon/verse data only.

import json
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

SESSION_FILENAME = "verseview_session.json"


# ── Path helpers ──────────────────────────────────────────────────────────────

def _user_data_dir() -> Path:
    """Return (and create) the cross-platform user-data directory for VerseView.
    Mirrors the logic in settings.py so both files live in the same folder.
    Survives app reinstalls and re-downloads on Intel Mac, Apple Silicon Mac,
    and Windows.
    """
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "VerseView"
    else:
        base = Path(os.getenv("APPDATA", str(Path.home()))) / "VerseView"
    base.mkdir(parents=True, exist_ok=True)
    return base


def get_session_path() -> str:
    """Return the full path of the session file (for logging/debug)."""
    return str(_user_data_dir() / SESSION_FILENAME)


# ── Public API ────────────────────────────────────────────────────────────────

def save_session(data: dict) -> None:
    """Write *data* to the session file atomically.

    Uses a .tmp intermediate so that a hard crash during the write never
    produces a corrupt session file.
    """
    try:
        target = _user_data_dir() / SESSION_FILENAME
        tmp    = target.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        # Atomic rename — on Windows os.replace() handles the same-drive case
        os.replace(tmp, target)
        logger.debug(f"💾 Session saved → {target}")
    except Exception as e:
        logger.warning(f"⚠️ Session save failed: {e}")


def load_session() -> dict | None:
    """Return the session dict if the file exists and is valid JSON, else None."""
    try:
        path = _user_data_dir() / SESSION_FILENAME
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or not data:
            return None
        return data
    except Exception as e:
        logger.warning(f"⚠️ Session load failed: {e}")
        return None


def clear_session() -> None:
    """Delete the session file if it exists."""
    try:
        path = _user_data_dir() / SESSION_FILENAME
        if path.exists():
            path.unlink()
            logger.debug("🗑️ Session file cleared.")
    except Exception as e:
        logger.warning(f"⚠️ Session clear failed: {e}")


def session_exists() -> bool:
    """Return True if a valid, non-empty session file is present."""
    return load_session() is not None
