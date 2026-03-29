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
    "gemini_api_key":             "",
    "cerebras_api_key":           "",
    "mistral_api_key":            "",
    "sarvam_api_key":             "",
    "discord_webhook_url":        "",
    "discord_log_webhook_url":    "",
    "discord_notes_webhook_url":  "",
    # ── Language / Input ──
    "language":                   "English (Nova-2)",
    "mic_index":                  0,
    "show_malayalam_raw":         False,
    # ── Display ──
    "remote_url":                 "http://localhost:50010/control.html",
    "display_screen":             "Display 2 (Right/Extended)",
    "bible_translation":          "KJV",
    # ── Audio / Timing ──
    "rate":                       16000,
    "chunk":                      4096,
    "cooldown":                   3.0,
    "dedup_window":               60,
    "silence_timeout":            60,
    # ── Detection Options ──
    "llm_enabled":                True,
    "confidence":                 0.75,
    "manual_confirm":             True,
    "verify":                     True,
    "verse_interrupt":            False,
    "spoken_numeral_mode":        False,
    "smart_amen":                 True,
    # ── App Behaviour ──
    "auto_save_notes":            True,
    "auto_start":                 False,
    "smart_schedule":             False,
    "panic_key":                  "esc",
    # ── Live Points ──
    "live_points_prompt":         "",
    "live_points_llm_enabled":    False,
    # ── ATEM Chroma Key Overlay ──
    "atem_enabled":               False,
    "atem_ip":                    "",
    "atem_key_duration":          5.0,
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


def export_settings(data: dict):
    path = fd.asksaveasfilename(
        title="Export VerseView Settings",
        defaultextension=".json",
        filetypes=[("JSON file", "*.json")],
        initialfile="verseview_settings.json",
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
    path = fd.askopenfilename(
        title="Import VerseView Settings",
        filetypes=[("JSON file", "*.json")],
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
