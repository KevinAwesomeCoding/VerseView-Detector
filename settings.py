import json
import sys
import os
from pathlib import Path
import tkinter.filedialog as fd
import tkinter.messagebox as mb

DEFAULTS = {
    # ── API Keys ──
    "deepgram_api_key":           "",
    "groq_api_key":               "",
    "gemini_api_key":             "",   # Google Gemini 2.0 Flash — preferred LLM (no rate limits)
    "sarvam_api_key":             "",
    # ── Discord webhooks ──
    "discord_webhook_url":        "",
    "discord_log_webhook_url":    "",
    "discord_notes_webhook_url":  "",
    # ── Audio / engine ──
    "language":                   "English (Nova-2)",
    "mic_index":                  0,
    "remote_url":                 "http://localhost:50010/control.html",
    "bible_translation":          "KJV",
    "rate":                       16000,
    "chunk":                      4096,
    "cooldown":                   3.0,
    "dedup_window":               60,
    "llm_enabled":                True,
    # ── Behaviour ──
    "confidence":                 0.75,
    "manual_confirm":             True,
    "verify":                     True,
    "smart_amen":                 True,
    "auto_save_notes":            True,
    "auto_start":                 False,
    "smart_schedule":             False,
    "panic_key":                  "esc",
    # ── Live Points ──
    "live_points_prompt":         "",
    "live_points_llm_enabled":    False,
    "display_screen":             "Display 2 (Right/Extended)",
}


def _settings_path() -> Path:
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "VerseView"
    else:
        base = Path(os.getenv("APPDATA", str(Path.home()))) / "VerseView"
    base.mkdir(parents=True, exist_ok=True)
    return base / "settings.json"


def load() -> dict:
    """Load saved settings, filling any missing keys from DEFAULTS."""
    path = _settings_path()
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                saved = json.load(f)
            return {**DEFAULTS, **saved}
        except Exception:
            pass
    return dict(DEFAULTS)


def save(data: dict):
    """Persist settings to disk."""
    path = _settings_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Could not save settings: {e}")


def export_settings(data: dict) -> bool:
    """Ask user for a file path and export settings as JSON."""
    path = fd.asksaveasfilename(
        title="Export VerseView Settings",
        defaultextension=".json",
        filetypes=[("JSON file", "*.json")],
        initialfile="verseview_settings.json"
    )
    if not path:
        return False
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        mb.showerror("Export Failed", str(e))
        return False


def import_settings() -> dict | None:
    """Let user pick a JSON file and merge it over DEFAULTS."""
    path = fd.askopenfilename(
        title="Import VerseView Settings",
        filetypes=[("JSON file", "*.json")]
    )
    if not path:
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {**DEFAULTS, **data}
    except Exception as e:
        mb.showerror("Import Failed", str(e))
        return None
