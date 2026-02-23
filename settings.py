import json
import sys
import os
from pathlib import Path

DEFAULTS = {
    # API Keys
    "deepgram_api_key":    "",
    "openrouter_api_key":  "",
    "discord_webhook_url": "",
    "sarvam_api_key":      "",
    # Basic settings
    "language":     "English (Nova-2)",
    "mic_index":    0,
    "remote_url":   "http://localhost:50010/control.html",
    # Advanced settings
    "rate":          16000,
    "chunk":         4096,
    "cooldown":      3.0,
    "dedup_window":  60,
    "llm_enabled":   True,
}


def _settings_path() -> Path:
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "VerseView"
    else:
        base = Path(os.getenv("APPDATA", str(Path.home()))) / "VerseView"
    base.mkdir(parents=True, exist_ok=True)
    return base / "settings.json"


def load() -> dict:
    path = _settings_path()
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                saved = json.load(f)
            # Merge with defaults so new keys always exist
            return {**DEFAULTS, **saved}
        except Exception:
            pass
    return dict(DEFAULTS)


def save(data: dict):
    path = _settings_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Could not save settings: {e}")
