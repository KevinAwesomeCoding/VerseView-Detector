import json
import sys
import os
import base64
import logging
from pathlib import Path
import tkinter.filedialog as fd
import tkinter.messagebox as mb

logger = logging.getLogger("VerseViewSTT")

DEFAULTS = {
    # ── API Keys ──
    "deepgram_api_key":           "",
    "groq_api_key":               "",
    "gemini_api_key":             "",
    "cerebras_api_key":           "",
    "mistral_api_key":            "",
    "sarvam_api_key":             "",
    "sarvam_api_key_backup":      "",
    "assemblyai_api_key":         "",
    "gladia_api_key":             "",
    "gcp_credentials_path":       "",
    "local_whisper_endpoint":     "http://127.0.0.1:8080",
    "discord_webhook_url":        "",
    "discord_log_webhook_url":    "",
    "discord_notes_webhook_url":  "",
    # ── STT Engine ──
    "stt_engine":                 "deepgram",
    "aai_turn_cutoff":            5,
    # ── Dual STT ──
    "dual_stt_enabled":           False,
    "secondary_language":         None,
    "secondary_stt_engine":       "deepgram",
    # ── Language / Input ──
    "language":                   "English",
    "mic_index":                  0,
    "show_malayalam_raw":         False,
    "malayalam_transliteration":  False,
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
    # ── Settings Sync ──
    "settings_sync_url":          "",
    # ── Discord Bot ──
    "discord_bot_token":          "",
    "vv_host":                    "127.0.0.1",
    "vv_port":                    "12345",
}

# ── Portable GCP credential transport ────────────────────────────────────────
# OPTIONAL, transport-only settings key. Holds an entire Google service-account
# JSON encoded as base64 text so credentials can ride inside an exported / synced
# settings JSON object and light up GCP on another machine. It is deliberately
# NOT part of DEFAULTS and is NEVER persisted in the local active settings.json:
# on load / import / sync it is materialised into the per-user managed credential
# store and then stripped, so the raw secret only ever exists transiently inside
# a file the user explicitly chose to export with credentials included.
GCP_CREDENTIALS_PAYLOAD_KEY = "gcp_credentials_payload"

# OPTIONAL secondary transport: a direct-download URL to a raw service-account
# JSON. Materialised the same way as the payload when present. The base64 payload
# remains the primary mechanism and works fully on its own.
GCP_CREDENTIALS_URL_KEY = "gcp_credentials_url"

# The four fields every Google service-account key file carries.
_GCP_SA_REQUIRED_KEYS = ("type", "project_id", "private_key", "client_email")


# ── Per-user writable app-data locations ─────────────────────────────────────
# These live OUTSIDE the packaged app bundle / .exe on every OS, so the auto
# updater (which only rewrites the app bundle / _internal folder / executable)
# never touches them — settings AND managed credentials survive updates.
#   macOS (Intel & Apple Silicon, identical):
#       ~/Library/Application Support/VerseView/
#   Windows:
#       %APPDATA%/VerseView/
#   Other (sane fallback):
#       ~/.verseview/
def _app_data_dir() -> Path:
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "VerseView"
    elif os.name == "nt":
        base = Path(os.getenv("APPDATA", str(Path.home()))) / "VerseView"
    else:
        base = Path.home() / ".verseview"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _settings_path() -> Path:
    return _app_data_dir() / "settings.json"


# ── Managed Google Cloud credential store ────────────────────────────────────
def get_managed_gcp_credentials_dir() -> Path:
    """Per-user directory that holds the app-managed GCP credential copy."""
    d = _app_data_dir() / "credentials"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_managed_gcp_credentials_path() -> str:
    """Absolute path of the app-managed service-account JSON for this user/OS:
    .../VerseView/credentials/gcp_service_account.json"""
    return str(get_managed_gcp_credentials_dir() / "gcp_service_account.json")


def has_managed_gcp_credentials() -> bool:
    """True when a managed GCP credential file is present on this machine."""
    return os.path.isfile(get_managed_gcp_credentials_path())


def validate_gcp_service_account_json(data) -> bool:
    """True when data is a dict that looks like a Google service-account key:
    a dict with type == "service_account" plus project_id, private_key and
    client_email."""
    if not isinstance(data, dict):
        return False
    if data.get("type") != "service_account":
        return False
    return all(data.get(k) for k in _GCP_SA_REQUIRED_KEYS)


def validate_service_account_text(text: str) -> bool:
    """True when text parses as a valid Google service-account JSON key."""
    try:
        return validate_gcp_service_account_json(json.loads(text))
    except Exception:
        return False


def validate_service_account_file(path: str) -> bool:
    """True when the file at path contains a valid service-account JSON."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return validate_service_account_text(f.read())
    except Exception:
        return False


def resolve_gcp_credentials_path(settings=None) -> str:
    """Return the final usable local GCP credentials path, or "" if none.

    Accepts either the whole settings dict or a raw path string. Priority:
      1. the stored gcp_credentials_path if it exists on disk — covers BOTH the
         managed copy and a legacy raw path a user may have pasted (backward
         compatible).
      2. the managed per-user credential file, if present — self-healing: works
         even when the stored path is blank or points at a file from another
         machine (e.g. a settings.json copied/synced across computers).
    """
    if isinstance(settings, dict):
        stored_path = settings.get("gcp_credentials_path", "")
    else:
        stored_path = settings or ""
    stored_path = (stored_path or "").strip()
    if stored_path and os.path.isfile(stored_path):
        return stored_path
    managed = get_managed_gcp_credentials_path()
    if os.path.isfile(managed):
        return managed
    return ""


def _write_managed_credential(text: str) -> str:
    """Write validated service-account JSON text to the managed store with
    best-effort restrictive permissions. Returns the managed path."""
    dest = get_managed_gcp_credentials_path()
    with open(dest, "w", encoding="utf-8") as f:
        f.write(text)
    try:
        os.chmod(dest, 0o600)   # best-effort: owner-only on POSIX
    except Exception:
        pass
    return dest


def import_gcp_credentials_file(path: str) -> str:
    """Validate a service-account JSON file and copy it into the managed store.

    Returns the managed path on success; raises ValueError on invalid input.
    """
    path = (path or "").strip()
    if not path or not os.path.isfile(path):
        raise ValueError(f"Credential file not found: {path}")
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception as exc:
        raise ValueError(f"Could not read credential file: {exc}") from exc
    if not validate_service_account_text(text):
        raise ValueError(
            "That file is not a valid Google service-account key. Expected JSON "
            "with type=service_account plus project_id, private_key and "
            "client_email."
        )
    dest = _write_managed_credential(text)
    logger.info("🔐 GCP service-account credential imported into managed store.")
    return dest


def read_gcp_credentials_payload() -> str | None:
    """Return the managed credential as a base64 payload, or None if absent/invalid.
    Used by export when the user opts to include credentials."""
    path = get_managed_gcp_credentials_path()
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        if not validate_service_account_text(text):
            return None
        return base64.b64encode(text.encode("utf-8")).decode("ascii")
    except Exception:
        return None


def materialize_gcp_credentials_payload(payload_b64: str) -> str | None:
    """Decode + validate a base64 service-account payload and write it to the
    managed store. Returns the managed path on success, or None on any failure
    (logs a clear reason; never raises)."""
    if not payload_b64 or not isinstance(payload_b64, str):
        return None
    try:
        text = base64.b64decode(payload_b64.encode("ascii")).decode("utf-8")
    except Exception:
        logger.warning("⚠️ GCP credential payload could not be base64-decoded — ignored.")
        return None
    if not validate_service_account_text(text):
        logger.warning("⚠️ GCP credential payload is not a valid service account — ignored.")
        return None
    try:
        dest = _write_managed_credential(text)
    except Exception as exc:
        logger.warning(f"⚠️ Could not write GCP credential from payload: {exc}")
        return None
    logger.info("🔐 GCP service-account credential materialised from portable payload.")
    return dest


def _materialize_gcp_url(url: str) -> str | None:
    """Optional secondary transport: download a raw service-account JSON from a
    direct URL and materialise it. Returns the managed path or None on failure."""
    url = (url or "").strip()
    if not url:
        return None
    try:
        import requests as _req, certifi as _cert
        r = _req.get(url, timeout=10, verify=_cert.where())
        r.raise_for_status()
        text = r.text
    except Exception as exc:
        logger.warning(f"⚠️ Could not download GCP credential from URL: {exc}")
        return None
    if not validate_service_account_text(text):
        logger.warning("⚠️ GCP credential URL did not return a valid service account — ignored.")
        return None
    try:
        dest = _write_managed_credential(text)
    except Exception as exc:
        logger.warning(f"⚠️ Could not write GCP credential from URL: {exc}")
        return None
    logger.info("🔐 GCP service-account credential materialised from URL.")
    return dest


def materialize_gcp_from_transport(source: dict) -> str | None:
    """Materialise a managed credential from a dict that may carry a base64
    payload (primary) or a credential URL (secondary). Returns the managed path
    on success, or None. Does NOT mutate source. Shared by load / import / sync
    so all three behave identically."""
    if not isinstance(source, dict):
        return None
    if source.get(GCP_CREDENTIALS_PAYLOAD_KEY):
        managed = materialize_gcp_credentials_payload(source[GCP_CREDENTIALS_PAYLOAD_KEY])
        if managed:
            return managed
    if source.get(GCP_CREDENTIALS_URL_KEY):
        return _materialize_gcp_url(source[GCP_CREDENTIALS_URL_KEY])
    return None


def _materialize_gcp_payload(data: dict) -> dict:
    """If data carries a portable GCP credential (base64 payload, or a URL as a
    secondary option), write it to the managed store and point
    gcp_credentials_path at the managed copy, then strip the transport-only keys
    so the raw secret is never persisted in the local settings file. Mutates +
    returns data."""
    if not isinstance(data, dict):
        return data
    managed = materialize_gcp_from_transport(data)
    if managed:
        data["gcp_credentials_path"] = managed
    # Always drop the transport-only keys — never persist a raw secret locally.
    data.pop(GCP_CREDENTIALS_PAYLOAD_KEY, None)
    data.pop(GCP_CREDENTIALS_URL_KEY, None)
    return data


def load() -> dict:
    path = _settings_path()
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                saved = json.load(f)
            merged = {**DEFAULTS, **saved}
            had_transport = bool(
                merged.get(GCP_CREDENTIALS_PAYLOAD_KEY)
                or merged.get(GCP_CREDENTIALS_URL_KEY)
            )
            merged = _materialize_gcp_payload(merged)
            # If a transport field was materialised + stripped, rewrite the
            # cleaned file so the raw secret never lingers in settings.json.
            if had_transport:
                save(merged)
            return merged
        except Exception:
            pass
    return dict(DEFAULTS)


def save(data: dict):
    path = _settings_path()
    try:
        # Defensive: never persist the transport-only fields in the local file.
        to_write = dict(data)
        to_write.pop(GCP_CREDENTIALS_PAYLOAD_KEY, None)
        to_write.pop(GCP_CREDENTIALS_URL_KEY, None)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(to_write, f, indent=2)
    except Exception as e:
        print(f"Could not save settings: {e}")


def export_settings(data: dict, include_gcp_credentials: bool = False):
    path = fd.asksaveasfilename(
        title="Export VerseView Settings",
        defaultextension=".json",
        filetypes=[("JSON file", "*.json")],
        initialfile="verseview_settings.json",
    )
    if not path:
        return False
    try:
        out = dict(data)
        out.pop(GCP_CREDENTIALS_PAYLOAD_KEY, None)
        out.pop(GCP_CREDENTIALS_URL_KEY, None)
        if include_gcp_credentials:
            payload = read_gcp_credentials_payload()
            if payload:
                out[GCP_CREDENTIALS_PAYLOAD_KEY] = payload
                # The source path is machine-specific; blank it so the importing
                # machine resolves to ITS managed copy after materialising.
                out["gcp_credentials_path"] = ""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)
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
        merged = {**DEFAULTS, **data}
        # Materialise any portable GCP credential into the managed store, set the
        # path to the local managed copy, and strip the secret from the dict.
        merged = _materialize_gcp_payload(merged)
        return merged
    except Exception as e:
        mb.showerror("Import Failed", str(e))
        return None
