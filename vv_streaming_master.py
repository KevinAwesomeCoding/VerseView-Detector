# -*- coding: utf-8 -*-
import sys, os

IS_WINDOWS = sys.platform.startswith("win")

import asyncio
import time
import re
import logging
import requests
import certifi
import threading
import datetime as _dt
import json

# ── Bot Bridge (Discord → Selenium) ──────────────────────────────────────────
try:
    from vv_bot_bridge import start_bot_bridge as _start_bot_bridge
except ImportError:
    _start_bot_bridge = None

from parse_reference_eng import parse_references as parse_eng, normalize_numbers_only as norm_eng, resolve_book as resolve_book_eng, set_spoken_numeral_mode
from parse_reference_hindi import parse_references as parse_hindi, normalize_numbers_only as norm_hindi
from parse_reference_ml import parse_references as parse_ml, normalize_numbers_only as norm_ml
from bible_fetcher import fetch_verse as multi_fetch, fetch_chapter as _fetch_chapter_raw

def fetch_chapter_verses(book: str, chapter: str) -> list:
    """GUI-callable: returns [{num, text}] for the current translation."""
    return _fetch_chapter_raw(book, chapter, BIBLE_TRANSLATION)

# Default to English normalizer until set_language() is called
normalize_numbers_only = norm_eng


# ── GROQ CLIENT  (verse extraction — llama-3.1-8b-instant) ──────────────────
class _GroqResponse:
    class _Choice:
        class _Msg:
            def __init__(self, content): self.content = content
        def __init__(self, content): self.message = self._Msg(content)
    def __init__(self, content): self.choices = [self._Choice(content)]

class _GroqCompletions:
    def __init__(self, api_key): self._key = api_key

    def create(self, model, messages, temperature=0.2, max_tokens=None, **kw):
        headers = {"Authorization": f"Bearer {self._key}", "Content-Type": "application/json"}
        body    = {"model": model, "messages": messages, "temperature": temperature}
        if max_tokens is not None:
            body["max_tokens"] = max_tokens
        for attempt in range(3):
            r = requests.post(  # type: ignore
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers, json=body, timeout=30, verify=certifi.where(),  # type: ignore
            )
            if r.status_code == 429:
                wait = min(2 ** attempt * 2, 8)
                logger.warning(f"⚠️ Groq rate limited (429) — retrying in {wait}s...")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return _GroqResponse(r.json()["choices"][0]["message"]["content"])  # type: ignore
        raise RuntimeError("Groq API rate limit exceeded after 3 retries")

class _GroqChat:
    def __init__(self, api_key): self.completions = _GroqCompletions(api_key)

class _GroqClient:
    """Groq — ONLY used for extract_verse_with_llm (fast, fires every few seconds)."""
    def __init__(self, api_key): self.chat = _GroqChat(api_key)


# ── CEREBRAS CLIENT  (live outline + sermon summary fallback — gpt-oss-120b) ─
# Global circuit breaker for Cerebras to prevent flooding after a 429 error
_cerebras_circuit_breaker_until = 0.0
# Proactive throttle: minimum gap between Cerebras calls (5 req/min → 12s apart)
_cerebras_last_call_time        = 0.0
_CEREBRAS_MIN_INTERVAL          = 12.0  # seconds between calls
# Bug 2: lock so concurrent threads cannot both pass the throttle check before updating the timestamp
_cerebras_call_lock             = threading.Lock()
_live_outline_last_dispatch     = 0.0    # Bug 2: min gap between consecutive outline dispatches
_LIVE_OUTLINE_COOLDOWN          = 20.0   # Bug 2: seconds
_groq_outline_call_times: list  = []     # Bug 3: timestamps of recent Groq outline calls
_GROQ_OUTLINE_RPM_LIMIT         = 5      # Bug 3: suppress outline after 5 Groq calls within 60s

class _CerebrasCompletions:
    def __init__(self, api_key): self._key = api_key

    def create(self, model, messages, temperature=0.2, max_tokens=None, **kw):
        global _cerebras_circuit_breaker_until, _cerebras_last_call_time

        # Bug 2: Atomic slot reservation — acquire lock, check circuit breaker, reserve timestamp,
        # then sleep OUTSIDE the lock so other threads can compute their own wait.
        with _cerebras_call_lock:
            now = time.time()
            if now < _cerebras_circuit_breaker_until:
                remaining = int(_cerebras_circuit_breaker_until - now)
                raise RuntimeError(f"Cerebras circuit breaker active (retry in {remaining}s)")
            # Reserve the next available call slot atomically
            next_slot = max(now, _cerebras_last_call_time + _CEREBRAS_MIN_INTERVAL)
            _cerebras_last_call_time = next_slot
        gap = next_slot - time.time()
        if gap > 0:
            logger.debug(f"Cerebras throttle: sleeping {gap:.1f}s to stay under rate limit")
            time.sleep(gap)

        headers = {"Authorization": f"Bearer {self._key}", "Content-Type": "application/json"}
        body    = {"model": model, "messages": messages, "temperature": temperature}
        if max_tokens is not None:
            body["max_completion_tokens"] = max_tokens

        for attempt in range(5):
            try:
                _cerebras_last_call_time = time.time()
                r = requests.post(
                    "https://api.cerebras.ai/v1/chat/completions",
                    headers=headers, json=body, timeout=60, verify=certifi.where(),
                )
                if r.status_code == 429:
                    # Respect Retry-After header if provided
                    retry_after = r.headers.get("Retry-After") or r.headers.get("retry-after")
                    if retry_after:
                        try:
                            wait = min(float(retry_after), 120)
                        except ValueError:
                            wait = min(5 * (2 ** attempt), 60)
                    else:
                        wait = min(5 * (2 ** attempt), 60)  # 5→10→20→40→60s
                    logger.warning(
                        f"⚠️ Cerebras rate limited (429) — "
                        f"{'Retry-After=' + str(retry_after) + 's' if retry_after else 'backoff=' + str(int(wait)) + 's'} "
                        f"(attempt {attempt+1}/5)"
                    )
                    if attempt == 4:
                        # All retries exhausted — set circuit breaker and give up
                        _cerebras_circuit_breaker_until = time.time() + wait
                        break
                    time.sleep(wait)  # sleep full backoff then retry
                    continue
                r.raise_for_status()
                return _GroqResponse(r.json()["choices"][0]["message"]["content"])
            except RuntimeError:
                raise
            except Exception as e:
                if attempt == 4:
                    raise e
                backoff = min(2 ** attempt, 8)
                logger.debug(f"Cerebras transient error (attempt {attempt+1}): {e} — retrying in {backoff}s")
                time.sleep(backoff)
        raise RuntimeError("Cerebras API failed after retries")

class _CerebrasChat:
    def __init__(self, api_key): self.completions = _CerebrasCompletions(api_key)

class _CerebrasClient:
    """Cerebras — live_points_loop outline + sermon summary fallback."""
    def __init__(self, api_key): self.chat = _CerebrasChat(api_key)


# ── MISTRAL CLIENT  (sermon summary primary — mistral-large-latest) ──────────
class _MistralCompletions:
    def __init__(self, api_key): self._key = api_key

    def create(self, model, messages, temperature=0.2, max_tokens=None, **kw):
        headers = {"Authorization": f"Bearer {self._key}", "Content-Type": "application/json"}
        body    = {"model": model, "messages": messages, "temperature": temperature}
        if max_tokens is not None:
            body["max_tokens"] = max_tokens
        r = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers=headers, json=body, timeout=90, verify=certifi.where(),
        )
        r.raise_for_status()
        return _GroqResponse(r.json()["choices"][0]["message"]["content"])

class _MistralChat:
    def __init__(self, api_key): self.completions = _MistralCompletions(api_key)

class _MistralClient:
    """Mistral — ONLY used for generate_sermon_summary (mistral-large-latest)."""
    def __init__(self, api_key): self.chat = _MistralChat(api_key)


# ── LOGGING ──────────────────────────────────────────────────────────────────
import io
session_log_stream = io.StringIO()
session_log_handler = logging.StreamHandler(session_log_stream)
session_log_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-5s %(message)s"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s %(message)s",
    handlers=[
        logging.FileHandler("verseview.log", encoding="utf-8"),
        logging.StreamHandler(),
        session_log_handler,
    ],
)
logger = logging.getLogger(__name__)


# ── DISCORD LIVE LOG ──────────────────────────────────────────────────────────
class _DiscordLiveLog:
    """One Discord message per session, edited every 5s with new log lines."""
    MAX_CHARS = 1900

    def __init__(self):
        self._msg_id        = None
        self._lines         = []
        self._dirty         = False
        self._lock          = threading.Lock()
        self._stop_evt      = threading.Event()
        self._close_message = ""   # Feature 7: custom caption when app closes without Stop
        threading.Thread(target=self._flush_loop, daemon=True).start()

    def _url(self):
        return DISCORD_LOG_WEBHOOK_URL.strip() if DISCORD_LOG_WEBHOOK_URL else ""

    def _build(self):
        h     = "**\U0001f3d9\ufe0f VerseView Live Log**\n```\n"
        f_end = "```"
        lines = list(self._lines)
        while lines and len(h) + len("\n".join(lines)) + len(f_end) > self.MAX_CHARS:
            lines.pop(0)
        return h + "\n".join(lines) + "\n" + f_end

    def _create(self):
        url = self._url()
        if not url:
            return
        try:
            r = requests.post(url + "?wait=true", json={"content": self._build()},
                              timeout=10, verify=certifi.where())
            if r.status_code in (200, 204):
                self._msg_id = r.json().get("id")
        except Exception as ex:
            logger.debug(f"Discord log create: {ex}")

    def _edit(self):
        url = self._url()
        if not url or not self._msg_id:
            return
        try:
            requests.patch(
                f"{url}/messages/{self._msg_id}",
                json={"content": self._build()}, timeout=10, verify=certifi.where(),
            )
        except Exception as ex:
            logger.debug(f"Discord log edit: {ex}")

    def append(self, line: str):
        with self._lock:
            self._lines.append(line)
            self._dirty = True

    def _flush_loop(self):
        while not self._stop_evt.is_set():
            self._stop_evt.wait(5)
            with self._lock:
                if not self._dirty:
                    continue
                self._dirty = False
                if self._msg_id is None:
                    self._create()
                else:
                    self._edit()

    def _delete(self):
        url = self._url()
        if not url or not self._msg_id:
            return
        try:
            requests.delete(f"{url}/messages/{self._msg_id}", timeout=10, verify=certifi.where())
            self._msg_id = None
        except Exception as ex:
            logger.debug(f"Discord log delete: {ex}")

    def _upload_log_file(self):
        url = self._url()
        if not url:
            return
        try:
            import datetime as _dt
            label   = _dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            caption = self._close_message or f"📋 **VerseView Session Log** — {label}"
            
            # Fetch log content from in-memory stream output
            log_content = session_log_stream.getvalue().encode("utf-8")
            if not log_content.strip():
                return
                
            requests.post(
                url,
                data={"content": caption},
                files={"file": (f"verseview_{label}.log", log_content, "text/plain")},
                timeout=30,
                verify=certifi.where(),
            )
        except Exception as ex:
            logger.debug(f"Discord log upload: {ex}")

    def set_close_message(self, msg: str):
        """Feature 7: override the upload caption (e.g. app closed without Stop)."""
        self._close_message = msg

    def stop(self):
        self._stop_evt.set()
        self._delete()
        self._upload_log_file()

    def reset(self):
        """Re-arm for a new session: clear state and restart the flush thread."""
        with self._lock:
            self._msg_id        = None
            self._lines         = []
            self._dirty         = False
            self._close_message = ""
        self._stop_evt.clear()
        t = threading.Thread(target=self._flush_loop, daemon=True)
        t.start()


class _DiscordLogHandler(logging.Handler):
    def __init__(self, live_log):
        super().__init__()
        self._live = live_log

    @staticmethod
    def _is_garbage_line(msg: str) -> bool:
        """Return True if this log line should be kept out of the Discord live feed.
        Criteria: the message body contains a large proportion of Malayalam Unicode
        characters, indicating an untranslated / garbled transcript blob that would
        appear as random script to Discord viewers.  The full log file still keeps
        every line."""
        # Strip the leading timestamp prefix ("HH:MM:SS ") before measuring
        body = msg[9:] if len(msg) > 9 else msg
        ml_chars = sum(1 for c in body if '\u0D00' <= c <= '\u0D7F')
        total    = len(body.replace(' ', ''))
        return total > 0 and (ml_chars / total) > 0.35

    def emit(self, record):
        if not DISCORD_LOG_WEBHOOK_URL:
            return
        try:
            import datetime as _dt
            if record.levelno >= logging.INFO:
                line = f"{_dt.datetime.now().strftime('%H:%M:%S')} {record.getMessage()}"
                if not self._is_garbage_line(line):
                    self._live.append(line)
        except Exception:
            pass


def send_sermon_notes_to_discord(notes: str):
    """Post sermon notes to DISCORD_NOTES_WEBHOOK_URL, chunked for Discord's 2000-char limit."""
    url = DISCORD_NOTES_WEBHOOK_URL.strip() if DISCORD_NOTES_WEBHOOK_URL else ""
    if not url:
        return
    LIMIT   = 1900
    header  = "📋 **Sermon Notes**\n"
    chunks  = []
    current = header
    for line in notes.splitlines():
        seg = line + "\n"
        if len(current) + len(seg) > LIMIT:
            chunks.append(current)
            current = seg
        else:
            current += seg
    if current.strip():
        chunks.append(current)
    for chunk in chunks:
        try:
            requests.post(url, json={"content": chunk}, timeout=10, verify=certifi.where())
            if len(chunks) > 1:
                import time as _t
                _t.sleep(0.5)
        except Exception as ex:
            logger.debug(f"Discord notes: {ex}")


_discord_live_log = _DiscordLiveLog()
logger.addHandler(_DiscordLogHandler(_discord_live_log))


# ── DEFAULTS ─────────────────────────────────────────────────────────────────
USE_XPATH             = sys.platform == "darwin"
USE_SARVAM            = False
show_malayalam_raw    = False
MALAYALAM_TRANSLITERATION = False
DEEPGRAM_LANGUAGE     = "en"
DEEPGRAM_MODEL        = "nova-3"
SARVAM_LANGUAGE       = "ml-IN"
PRIMARY_PARSER        = parse_eng
MIC_INDEX             = 1
RATE                  = 16000
CHUNK                 = 4096
REMOTE_URL            = "http://localhost:50010/control.html"
DEDUP_WINDOW          = 60
COOLDOWN              = 3.0
LLM_ENABLED           = True
LLM_CALL_COUNT           = 0
_llm_in_flight           = False
_llm_last_key            = None
_llm_last_time           = 0.0
_llm_last_dispatch_len   = 0    # Bug 5: track transcript length at last LLM dispatch
_last_explicit_ref_time  = 0.0  # Bug 3: timestamp of last explicitly-anchored ref delivery
_EXPLICIT_REF_EXPIRY     = 90.0 # seconds — thematic-only LLM hits require a recent explicit ref
_last_book_context_book  = None  # Bug 3+4: dedup — last book set by _apply_book_context_if_mentioned
_last_book_context_hash  = None  # Bug 4: hash of matched phrase to detect re-fires from same text
_last_book_context_time  = 0.0   # Bug 3: timestamp of last book context update
_BOOK_CONTEXT_STALE_SEC  = 120.0 # warn if context hasn't been refreshed in this many seconds
_BOOK_CONTEXT_CASUAL_RE  = re.compile(
    r'\b(?:taking\s+(?:it\s+)?from|reminded?\s+(?:me|us)\s+of'
    r'|you\s+know[\s,]+like|like\s+in|as\s+in|in\s+the\s+story\s+of'
    r'|(?:the\s+|a\s+)?[a-z]+\s+(?:who|that|which)\s+(?:said|told|spoke|wrote|taught|preached|proclaimed|declared|killed|was))\b',
    re.IGNORECASE,
)

# Bug 1 fix: Narrative / third-person reading guard.
# Phrases like "he was reading Isaiah 53" or "the Ethiopian found reading the book of Isaiah"
# are story narration — the current PREACHER is not announcing a passage switch.
# If one of these phrases precedes a book name we should NOT update context or present a verse.
# Extended: also catches person-title constructions like "Joel the prophet spoke about..."
# or "Matthew the tax collector" which are biographical references, not book anchors.
_NARRATIVE_READING_RE = re.compile(
    r'\b(?:'
    r'(?:he|she|they|the\s+\w+)\s+was\s+reading'       # "he was reading Isaiah"
    r'|(?:he|she|they)\s+were\s+reading'
    r'|(?:found|finds|seeing|saw)\s+(?:him|her|them|the\s+\w+)\s+reading'
    r'|(?:was|were)\s+(?:found\s+)?reading\s+from'
    r'|had\s+been\s+reading'
    r'|reading\s+from\s+the\s+(?:scroll|book|passage)\s+of'  # "reading from the scroll of Isaiah"
    r'|the\s+(?:scroll|passage|section|text|portion)\s+(?:he|she|they)\s+was\s+reading'
    # Person-title constructions that identify a name as a person, not a book:
    r'|(?:john|matthew|mark|luke|james|ruth|joel|job|amos|jonah|micah|peter|'
    r'jude|hosea|nahum|philemon|timothy|titus)\s+the\s+'
    r'(?:baptist|prophet(?:ess)?|apostle|disciple|evangelist|elder|'
    r'tax\s+collector|zealot|righteous|beloved|just)'
    r'|(?:the\s+)?(?:prophet|apostle|disciple|evangelist|elder)\s+'
    r'(?:john|matthew|mark|luke|james|joel|amos|jonah|micah|peter|jude|hosea|nahum)'
    r')\b',
    re.IGNORECASE,
)


def _get_contextual_anchor() -> tuple:
    """Return (book, chapter, verse) to use for contextual 'verse N' resolution.

    While a cross-reference overlay is active (within _XREF_ANCHOR_TTL seconds),
    contextual phrases like 'verse nine' should resolve against the *sermon* anchor,
    not the cross-reference that was just presented.  Once the TTL expires the xref
    overlay is considered gone and we fall back to current_book/chapter/verse.

    Logs the decision so operators can see why a particular anchor was chosen.
    """
    global _xref_anchor_book, _xref_anchor_chapter, _xref_anchor_verse, _xref_anchor_time

    xref_age = time.time() - _xref_anchor_time if _xref_anchor_time else float('inf')
    xref_active = (
        _xref_anchor_book is not None
        and xref_age < _XREF_ANCHOR_TTL
        and _sermon_anchor_book is not None
    )

    if xref_active:
        logger.debug(
            f"🎯 ANCHOR: using SERMON ANCHOR {_sermon_anchor_book} {_sermon_anchor_chapter}:"
            f"{_sermon_anchor_verse or '?'} "
            f"(xref {_xref_anchor_book} {_xref_anchor_chapter}:{_xref_anchor_verse or '?'} "
            f"active, age={xref_age:.0f}s — contextual 'verse N' stays on sermon)"
        )
        return _sermon_anchor_book, _sermon_anchor_chapter, _sermon_anchor_verse

    if _xref_anchor_book is not None and xref_age >= _XREF_ANCHOR_TTL:
        # TTL expired — quietly drop the xref overlay
        _xref_anchor_book    = None
        _xref_anchor_chapter = None
        _xref_anchor_verse   = None
        _xref_anchor_time    = 0.0
        logger.debug("📎 XREF ANCHOR expired — reverting to current context")

    logger.debug(
        f"🎯 ANCHOR: using CURRENT CONTEXT {current_book} {current_chapter}:{current_verse or '?'}"
    )
    return current_book, current_chapter, current_verse


def _is_narrative_reading_context(text: str, book_name: str) -> bool:
    """Return True if 'book_name' appears in 'text' as part of a narrative
    description of *someone else* reading (e.g. 'he was reading Isaiah 53')
    rather than the preacher directly announcing a passage.

    When True, callers should skip any context switch or verse presentation
    that would result from the detected book reference.
    """
    m_narr = _NARRATIVE_READING_RE.search(text)
    if not m_narr:
        return False
    # The narrative phrase must appear BEFORE the book name in the sentence.
    m_book = re.search(rf'\b{re.escape(book_name)}\b', text, re.IGNORECASE)
    if not m_book:
        return False
    if m_narr.start() < m_book.start():
        logger.info(
            f"📖 NARRATIVE reading guard triggered: "
            f"'{m_narr.group(0).strip()}' precedes '{book_name}' — skipping context switch"
        )
        return True
    return False
# Bug 5: self-correction marker — discard text before the marker when parsing references
_CORRECTION_RE = re.compile(
    r'\b(sorry|i mean|i meant|excuse me)\b',
    re.IGNORECASE,
)
BIBLE_TRANSLATION     = "web"
DEEPGRAM_API_KEY      = ""
GROQ_API_KEY          = ""
GEMINI_API_KEY        = ""
CEREBRAS_API_KEY      = ""
MISTRAL_API_KEY       = ""
DISCORD_WEBHOOK_URL         = ""
DISCORD_LOG_WEBHOOK_URL     = ""
DISCORD_NOTES_WEBHOOK_URL   = ""
SARVAM_API_KEY        = ""
ASSEMBLYAI_API_KEY    = ""
STT_ENGINE            = "deepgram"   # "deepgram" | "assemblyai"
AAI_LANGUAGE          = "en"         # "en" | "hi" | "ml" | "multi"
AAI_TURN_CUTOFF_SEC   = 5            # force_endpoint interval in seconds (3–11)

CONFIDENCE_THRESHOLD   = 0.75
REQUIRE_MANUAL_CONFIRM = True
CONFIRM_CALLBACK       = None
REQUIRE_VERIFY         = True
_vtc_pending_ref     = None
_vtc_trigger_words   = [] 
_vtc_timer          = None
PANIC_KEY              = "esc"

LIVE_POINTS_PROMPT         = ""
LIVE_POINTS_CALLBACK       = None
LIVE_POINTS_GET_CURRENT_CB = None

SMART_AMEN_ENABLED  = True
SMART_AMEN_KEYWORDS = [
    "let us pray",
    "let's pray",
    "please be seated",
    "bow our heads",
    "thank you jesus",
]
# Bug 4 fix: Smart Amen debounce timer (cancelled by panic key or new speech)
_smart_amen_timer: threading.Timer | None = None

VERSE_INTERRUPT_ENABLED  = False
SPOKEN_NUMERAL_MODE      = False
WORSHIP_MODE             = False
_verse_history: list     = []

# ── SCRIPTURE-READ MODE ───────────────────────────────────────────────────────
# Activated when the speaker signals a live bilingual / line-by-line Bible
# reading (e.g. "open your Bibles", "let's read", "I will read in English").
# While active the engine locks to the current book+chapter anchor and only
# accepts:
#   • the current verse
#   • the next verse in sequence
#   • an explicitly-requested verse in the same passage
# All stray numerals (sermon point counts, timestamps, crowd noise) and
# paraphrase fragments are suppressed unless they carry a clear verse signal.
SCRIPTURE_READ_MODE:          bool = False
_sr_locked_book:              str  = None   # book locked at entry
_sr_locked_chapter:           str  = None   # chapter locked at entry
_sr_expected_verse:           int  = None   # next verse the engine expects
_sr_entry_time:               float = 0.0   # when SCRIPTURE-READ was entered
_sr_last_language_hint:       str  = None   # "en" | "ml" | "hi" — current read language

# Phrases that trigger entry into SCRIPTURE-READ mode (case-insensitive)
_SR_ENTRY_PATTERNS = re.compile(
    r'\b(?:'
    r'open\s+your\s+bibles?'
    r'|let[\'s]*\s+(?:now\s+)?read'
    r'|(?:I|we)\s+(?:will|shall|am\s+going\s+to)\s+read'
    r'|read(?:ing)?\s+(?:from|in)\s+(?:english|malayalam|hindi|tamil|kannada|telugu|the\s+bible)'
    r'|I\s+(?:will|shall)\s+read\s+in\s+(?:english|malayalam|hindi|tamil|kannada|telugu)'
    r'|read\s+(?:together\s+)?(?:from\s+)?verse'
    r'|reading\s+(?:together|aloud|now)'
    r')\b',
    re.IGNORECASE,
)

# Stray-numeral patterns suppressed while SCRIPTURE-READ is active:
#   • timestamps  (12:30, 9:45 am/pm)
#   • sermon point numbers  (point 1, point one, first point, 1.)
#   • percentage/statistics  (50%, 30 percent)
#   • year references  (in 2024, year 1948)
_SR_STRAY_NUMERAL_RE = re.compile(
    r'(?:'
    r'\b\d{1,2}:\d{2}\s*(?:am|pm|a\.m\.|p\.m\.)\b'       # timestamps
    r'|\bpoint\s+(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)\b'  # sermon points
    r'|\b(?:first|second|third)\s+point\b'
    r'|\b\d+\.\s+(?=[A-Z])'                               # "1. Next idea"
    r'|\b\d+\s*%'                                         # percentages
    r'|\b\d+\s+percent\b'
    r'|\b(?:in\s+the\s+year|in|around|about|since|before|after)\s+\d{3,4}\b'  # year context
    r')',
    re.IGNORECASE,
)

# Exit signals — clear topic shift away from reading (e.g. sermon application)
_SR_EXIT_PATTERNS = re.compile(
    r'\b(?:'
    r'let\s+(?:me|us|\'s)\s+(?:now\s+)?(?:pray|preach|look\s+at|turn\s+to|talk\s+about)'
    r'|(?:sermon\s+)?(?:point|outline)\s+(?:number\s+)?\d+'
    r'|in\s+conclusion'
    r'|in\s+summary'
    r'|let\s+me\s+explain'
    r'|(?:this\s+(?:morning|evening|night)\s+)?(?:we\s+are\s+)?(?:going\s+to\s+)?(?:study|preach|teach|discuss)'
    r')\b',
    re.IGNORECASE,
)


def _enter_scripture_read_mode(language_hint: str = None) -> None:
    """Enter SCRIPTURE-READ mode, locking to the current book+chapter anchor."""
    global SCRIPTURE_READ_MODE, _sr_locked_book, _sr_locked_chapter
    global _sr_expected_verse, _sr_entry_time, _sr_last_language_hint
    if SCRIPTURE_READ_MODE:
        return  # already active
    anchor_book, anchor_chapter, anchor_verse = _get_contextual_anchor()
    if not anchor_book or not anchor_chapter:
        logger.info("📖 SCRIPTURE-READ: no anchor set — mode NOT entered (no book/chapter context)")
        return
    SCRIPTURE_READ_MODE     = True
    _sr_locked_book         = anchor_book
    _sr_locked_chapter      = anchor_chapter
    _sr_expected_verse      = (int(anchor_verse) if anchor_verse else None)
    _sr_entry_time          = time.time()
    _sr_last_language_hint  = language_hint
    logger.info(
        f"📖 SCRIPTURE-READ MODE ENTERED — locked to {_sr_locked_book} {_sr_locked_chapter}"
        f" (next expected v{_sr_expected_verse or '?'}) lang={language_hint or 'auto'}"
    )


def _exit_scripture_read_mode(reason: str = "manual") -> None:
    """Exit SCRIPTURE-READ mode and clear locked state."""
    global SCRIPTURE_READ_MODE, _sr_locked_book, _sr_locked_chapter
    global _sr_expected_verse, _sr_entry_time, _sr_last_language_hint
    if not SCRIPTURE_READ_MODE:
        return
    SCRIPTURE_READ_MODE    = False
    _sr_locked_book        = None
    _sr_locked_chapter     = None
    _sr_expected_verse     = None
    _sr_entry_time         = 0.0
    _sr_last_language_hint = None
    logger.info(f"📖 SCRIPTURE-READ MODE EXITED ({reason})")


def _scripture_read_check_entry_exit(text: str) -> None:
    """
    Inspect a raw transcript sentence for SCRIPTURE-READ entry/exit signals.
    Called early in _process_transcript_blob so the mode flag is up-to-date
    before the verse-detection layers run.
    """
    global _sr_expected_verse, _sr_last_language_hint

    # ── Entry detection ───────────────────────────────────────────────────────
    if not SCRIPTURE_READ_MODE:
        m_entry = _SR_ENTRY_PATTERNS.search(text)
        if m_entry:
            # Detect language hint if present
            lang_hint = None
            if re.search(r'\bmalayalam\b', text, re.IGNORECASE):
                lang_hint = "ml"
            elif re.search(r'\bhindi\b', text, re.IGNORECASE):
                lang_hint = "hi"
            elif re.search(r'\benglish\b', text, re.IGNORECASE):
                lang_hint = "en"
            _enter_scripture_read_mode(language_hint=lang_hint)
        return

    # ── Already in SCRIPTURE-READ — check for exit signals ───────────────────

    # 1. Language-switch hint update (bilingual reading — no exit, just update)
    if re.search(r'\b(?:now\s+)?(?:in|I\s+will\s+read\s+in)\s+(english|malayalam|hindi|tamil|kannada|telugu)\b',
                 text, re.IGNORECASE):
        m_lang = re.search(r'\b(english|malayalam|hindi|tamil|kannada|telugu)\b', text, re.IGNORECASE)
        if m_lang:
            new_lang = {"english": "en", "malayalam": "ml", "hindi": "hi",
                        "tamil": "ta", "kannada": "kn", "telugu": "te"}.get(m_lang.group(1).lower())
            if new_lang and new_lang != _sr_last_language_hint:
                _sr_last_language_hint = new_lang
                logger.info(f"📖 SCRIPTURE-READ: language hint updated → {new_lang}")
        return  # Never exit on a language-switch mid-reading

    # 2. Clear new anchor in a DIFFERENT book or chapter → exit
    # (handled externally in set_context / deliver_verse — see deliver_verse patch below)

    # 3. Explicit exit keywords (topic shift)
    if _SR_EXIT_PATTERNS.search(text):
        _exit_scripture_read_mode(reason="topic-shift keyword")
        return


def _scripture_read_filter(text: str) -> str:
    """
    When SCRIPTURE-READ is active, scrub stray numerals that are NOT verse
    signals before handing the text to the detection layers.
    Returns the cleaned text (may be unchanged if nothing was scrubbed).
    """
    if not SCRIPTURE_READ_MODE:
        return text
    cleaned = _SR_STRAY_NUMERAL_RE.sub("", text)
    if cleaned != text:
        logger.debug(f"📖 SR-FILTER: scrubbed stray numerals → '{cleaned.strip()}'")
    return cleaned


def _scripture_read_verse_allowed(ref: str) -> bool:
    """
    Returns True if *ref* is admissible while SCRIPTURE-READ is active.
    Admissible means:
      • Same locked book and chapter   AND
      • Verse is the expected next verse, the current verse, or at most 2 ahead
        (to handle minor mis-transcriptions), OR
      • Verse was explicitly stated in the current transcript excerpt
        (caller responsibility — just call with any explicitly-parsed ref).
    Cross-book or cross-chapter refs are blocked.
    """
    if not SCRIPTURE_READ_MODE:
        return True  # no restriction outside the mode
    if not _sr_locked_book or not _sr_locked_chapter:
        return True  # guard: mode entered without anchor — be permissive

    parts = ref.split()
    if ":" not in parts[-1]:
        # Chapter-only ref — allow if same locked book/chapter
        ref_book    = " ".join(parts)
        ref_chapter = None
    else:
        ref_chapter = parts[-1].split(":")[0]
        ref_book    = " ".join(parts[:-1])
        verse_str   = parts[-1].split(":")[1]

    # Book must match
    if ref_book.lower() != _sr_locked_book.lower():
        logger.debug(f"📖 SR-BLOCK: {ref} — wrong book (locked={_sr_locked_book})")
        return False

    # Chapter must match
    if ref_chapter and ref_chapter != _sr_locked_chapter:
        logger.debug(f"📖 SR-BLOCK: {ref} — wrong chapter (locked={_sr_locked_chapter})")
        return False

    # Verse window check
    if ref_chapter:
        try:
            v = int(verse_str)
            if _sr_expected_verse is not None:
                # Allow: expected, expected-1 (current), expected+1, expected+2
                if not (_sr_expected_verse - 1 <= v <= _sr_expected_verse + 2):
                    logger.debug(
                        f"📖 SR-BLOCK: {ref} — verse {v} outside window "
                        f"[{max(1,_sr_expected_verse-1)}..{_sr_expected_verse+2}] "
                        f"(expected={_sr_expected_verse})"
                    )
                    return False
        except ValueError:
            pass  # non-numeric verse — let through

    return True


def scripture_read_advance_expected(verse_num: int) -> None:
    """Called by deliver_verse when a verse is shown during SCRIPTURE-READ mode
    to advance the expected-next-verse pointer."""
    global _sr_expected_verse
    if SCRIPTURE_READ_MODE and verse_num is not None:
        _sr_expected_verse = verse_num + 1
        logger.debug(f"📖 SR: expected verse advanced → {_sr_expected_verse}")

# ── LLM CLIENTS (initialised in configure()) ─────────────────────────────────
groq_client     = None   # verse extraction only            (Groq llama-3.1-8b-instant)
cerebras_client = None   # live outline + summary fallback  (Cerebras gpt-oss-120b)
mistral_client  = None   # sermon summary primary           (Mistral mistral-large-latest)

# Bug 4: track highest verse presented per chapter this session so returning to
# a chapter resumes from the last known verse instead of re-presenting bare chapter.
_session_verse_high_water: dict = {}  # "Book chapter" → highest verse int seen this session

# Bug ML-3 fix: track last-presented verse number so contextual detection can
# reject backward jumps (e.g. jumping back to v1 when sermon is at v17).
_last_presented_verse_num: int = 0        # ordinal of last verse sent to display
_last_presented_verse_book_chap: str = "" # "Book chapter" key matching the above

# ── HARD CONFIRMATION GATE ────────────────────────────────────────────────────
# The hard confirmation gate has been REMOVED.  Previously, inferred detections
# (PARSER, CONTEXTUAL, SEQUENTIAL, LLM, RANGE, READ-INTENT, etc.) were held in a
# 45-second confirmation window and required two independent hits before firing.
# This caused unacceptable latency — the preacher would say a verse and the
# display would not update until the second hit (or not at all).
#
# Now, all detections pass straight through.  The individual layers have their
# own internal guards (e.g. LLM has anchor-match suppression + hardened prompt).
# The gate variables below are kept as no-ops for backward compatibility with
# any external code that might reference them, but they are no longer used.
_GATE_WINDOW_SECS: float = 0.0    # DEPRECATED — gate removed
_gate_pending: dict = {}          # DEPRECATED — gate removed

# ── Contextual-floor bypass flags ──────────────────────────────────────────────
# CONTEXT_FLOOR_EXPLICIT_BYPASS: when True, the ML-3 backward-jump floor is
# skipped for any transcript that contains an explicit book + chapter + verse
# reference (e.g. "Daniel 11:5", "Acts chapter 9 verse 15").  Explicit refs are
# always allowed regardless of what verse was last presented.
CONTEXT_FLOOR_EXPLICIT_BYPASS: bool = True

# ── SYSTEM-ACTION QUARANTINE ──────────────────────────────────────────────────
# When the operator performs a manual context change, clicks the chapter browser,
# injects verse history, or restores a session snapshot, the engine enters a
# short quarantine window.  During that window all *inferred* detections
# (CONTEXTUAL, SEQUENTIAL, LLM, RANGE, READ-INTENT, PARSER, SIMPLE …) are
# suppressed unless fresh spoken evidence arrives — i.e. the live transcript has
# grown by at least _QUARANTINE_MIN_NEW_CHARS characters AND the new tail
# contains an explicit verse signal (full ref, or "verse N" keyword).
#
# This is the OPPOSITE of the old CONTEXT_FLOOR_MANUAL_CONTEXT_BYPASS behaviour.
# Previously set_context() LOWERED the contextual floor for 30 s (making it
# easier to fire inferred detections).  That caused system-side navigation to
# silently steer the parser.  The quarantine instead RAISES the bar: manual /
# system events are metadata only; spoken intent is still required.
#
# Sources that ALWAYS bypass the quarantine (no change):
#   FAST-PATH, TRANSLATION-PATH, QUEUE, NEXT VERSE, ONWARDS
# (These require either an explicit spoken ref or are already in locked mode.)
#
# The old flag is kept with its name so callers compile; its logic is inverted.
CONTEXT_FLOOR_MANUAL_CONTEXT_BYPASS: bool = True   # now means "quarantine on manual set"
_MANUAL_CONTEXT_BYPASS_WINDOW: float       = 45.0  # quarantine length in seconds
_manual_context_set_time: float            = 0.0   # timestamp of last quarantine-opening event
_quarantine_transcript_offset: int         = 0     # len(full_sermon_transcript) when quarantine opened
_QUARANTINE_MIN_NEW_CHARS: int             = 40    # chars of new speech needed to clear quarantine early
LIVE_POINTS_ENABLED  = False   # Bug 8: guard — True only when LLM outline is enabled
SILENCE_TIMEOUT      = 60      # Feature 6: auto-stop after N seconds without a transcript line
_last_transcript_time = 0.0    # Feature 6: timestamp of last received transcript line
# Bug 1: latch to prevent RANGE_DETECTED from re-firing on the same passage
_range_latch_active = False
_range_latch_ref = None  # Track which reference triggered the range latch
# Bug 2: track last presented book+chapter for deduplication
_last_presented_book_chapter = None
_last_presented_time = 0.0
# Bug 3: track last processed sentence to detect repetitions
_last_sentence = None

# ── DUAL STT GLOBALS ──────────────────────────────────────────────────────────
DUAL_STT_ENABLED              = False
SECONDARY_LANGUAGE            = None   # "en" | "hi" | "ml"
SECONDARY_PARSER              = None   # parse_eng / parse_hindi / parse_ml
SECONDARY_DEEPGRAM_LANGUAGE   = "en"
SECONDARY_DEEPGRAM_MODEL      = "nova-3"
SECONDARY_USE_SARVAM          = False
SECONDARY_STT_ENGINE          = "deepgram"   # "deepgram" | "sarvam" | "assemblyai"
full_sermon_transcript_secondary = ""  # clean secondary-only buffer

# ── Issue B: SEC-ML repetition / noise detector ───────────────────────────────
# Detects extreme token-loop degeneration (e.g. "I I I…", "go to go to…").
# Triggered independently for each stream via _is_degenerate_chunk().
#
# Tuning constants:
#   _REP_MIN_TOKEN_LOOP  – minimum distinct-token repetitions before a 1-token
#                          or 2-token loop is considered degenerate (default 6).
#   _REP_MIN_PHRASE_LOOP – same for 3-token phrases (default 4).
#   _REP_DROP_WINDOW_SEC – after a degenerate chunk is dropped, further chunks
#                          from the same tag are throttled for this many seconds.
#
_REP_MIN_TOKEN_LOOP  : int   = 6    # "I I I I I I" → drop
_REP_MIN_PHRASE_LOOP : int   = 4    # "go to go to go to go to" → drop
_REP_DROP_WINDOW_SEC : float = 3.0  # throttle window after a drop (per stream tag)
_rep_drop_until      : dict  = {}   # tag → timestamp; chunks silenced until then

_sarvam_ignore_until = 0.0
_blocked_context_hashes = {}
_BLOCKED_DEDUP_SECS = 30.0
_MAX_VERSE_NUMBER = 200

# ── Discord send dedup (Bug 4: dual-STT duplicate posts) ─────────────────────
# Both AAI and SEC streams share the same VerseController and dedup window, but
# send_to_discord() is called inside send_verse() which IS protected by _send_lock.
# However the lock only serialises sends — if the two streams race and each passes
# the dedup checks before the other's history entry is written, both fire.
# Guard with a dedicated set + timestamp so the second send within 5 s is dropped.
_discord_sent: dict = {}       # ref → last sent timestamp
_DISCORD_DEDUP_SECS = 5.0      # window within which duplicate Discord posts are suppressed

# ── ATEM Chroma Key Overlay ──────────────────────────────────────────────────
ATEM_ENABLED      = False
ATEM_IP           = ""              # blank = auto-discover via mDNS/ARP
ATEM_KEY_DURATION = 5.0   # seconds the upstream keyer stays ON
_RANGE_INDICATOR_RE = re.compile(
    r'\b(?:through|thru|until)\b|മുതൽ|വരെ',
    re.IGNORECASE,
)

# BUG 2 (Auto-Stop Crash): Global shutdown flag — set before any resource teardown.
# All background threads (QUEUE, ONWARDS, VTC, LLM) check this at the top of every
# loop/task and exit immediately if set, preventing crashes on shared resource access.
_shutdown_flag = threading.Event()
_active_bg_threads: list = []  # Registry of all spawned background threading.Thread objects

# ── GLOBALS & SERMON BUFFER ──────────────────────────────────────────────────
stop_event             = None
_force_stopped         = False   # set by force_stop(); cleared in configure()
engine_loop            = None
_controller            = None
full_sermon_transcript = ""
verses_cited           = []


# ── STOP & PANIC ─────────────────────────────────────────────────────────────
def request_stop():
    global stop_event, engine_loop
    if engine_loop and stop_event:
        engine_loop.call_soon_threadsafe(stop_event.set)


def is_live_points_enabled() -> bool:
    """Bug 8: Returns True if the AI live outline feature is currently enabled."""
    return LIVE_POINTS_ENABLED


def trigger_panic():
    global _controller
    _cancel_smart_amen_timer()  # Bug 4: cancel any armed Smart Amen clear
    if _controller:
        _controller.close_presentation()


# ── SMART AMEN ───────────────────────────────────────────────────────────────
def _cancel_smart_amen_timer():
    """Cancel any pending Smart Amen clear (called by panic key or detect_verse_hybrid)."""
    global _smart_amen_timer
    if _smart_amen_timer:
        _smart_amen_timer.cancel()
        _smart_amen_timer = None


def check_smart_amen(text, controller):
    """Bug 4 fix: require end-of-text position, no following words, and 2.5s debounce."""
    global _smart_amen_timer
    if not SMART_AMEN_ENABLED:
        return False
    text_lower = text.lower().strip()
    text_len   = len(text_lower)

    for kw in SMART_AMEN_KEYWORDS:
        pos = text_lower.find(kw)
        if pos == -1:
            continue

        # (a) Position check: keyword must appear in the last 60% of the text
        if text_len > 0 and pos < text_len * 0.60:
            logger.debug(f"🙏 Smart Amen suppressed: '{kw}' too early in text (pos {pos}/{text_len})")
            continue

        # (b) No-following-words guard: allow only punctuation/whitespace after keyword
        after_kw       = text_lower[pos + len(kw):].strip()
        after_stripped = re.sub(r'^[\.,!?;:\s]+', '', after_kw)
        trailing_words = [w for w in after_stripped.split() if len(w) > 2]
        if len(trailing_words) > 4:
            logger.debug(
                f"🙏 Smart Amen suppressed: '{kw}' followed by more speech: '{after_kw[:40]}'"
            )
            continue

        # (c) Debounce: schedule the clear 2.5s in the future so panic key can cancel it
        _cancel_smart_amen_timer()
        logger.info(f"🙏 Smart Amen armed (2.5s debounce) by phrase: '{kw}'")

        def _do_clear(ctrl=controller, keyword=kw):
            global _smart_amen_timer
            _smart_amen_timer = None
            logger.info(f"🙏 Smart Amen triggered: closing presentation (keyword: '{keyword}')")
            ctrl.close_presentation()

        _smart_amen_timer = threading.Timer(2.5, _do_clear)
        _smart_amen_timer.daemon = True
        _smart_amen_timer.start()
        return True

    return False


# ── LIVE POINTS LOOP  (Cerebras → Groq fallback) ─────────────────────────────
async def live_points_loop():
    global full_sermon_transcript, LLM_ENABLED, groq_client, cerebras_client
    global LIVE_POINTS_PROMPT, LIVE_POINTS_CALLBACK, LIVE_POINTS_GET_CURRENT_CB
    global LIVE_POINTS_ENABLED, _live_outline_last_dispatch, _groq_outline_call_times

    last_processed_length = 0

    while not stop_event.is_set():
        await asyncio.sleep(90)

        # Bug 8: respect the Live Points enabled toggle — do nothing when it is off
        if not LIVE_POINTS_ENABLED:
            continue

        if not LLM_ENABLED or (not cerebras_client and not groq_client) or not LIVE_POINTS_CALLBACK:
            continue

        # Bug 2: minimum 20s between consecutive outline dispatches
        now_disp = time.time()
        if now_disp - _live_outline_last_dispatch < _LIVE_OUTLINE_COOLDOWN:
            continue

        current_transcript = full_sermon_transcript.strip()
        if len(current_transcript) < 150 or len(current_transcript) <= last_processed_length + 50:
            continue

        last_processed_length       = len(current_transcript)
        _live_outline_last_dispatch = time.time()

        current_display = LIVE_POINTS_GET_CURRENT_CB().strip() if LIVE_POINTS_GET_CURRENT_CB else ""
        if current_display:
            prompt = (
                f"{LIVE_POINTS_PROMPT}\n\n"
                f"Current Outline (may include manual edits — preserve and build on this):\n{current_display}\n\n"
                f"Full Transcript:\n{current_transcript}"
            )
        else:
            prompt = f"{LIVE_POINTS_PROMPT}\n\nTranscript:\n{current_transcript}"

        try:
            def fetch_points():
                # Cerebras live outline generation
                if cerebras_client:
                    try:
                        response = cerebras_client.chat.completions.create(
                            model="gpt-oss-120b",
                            messages=[{"role": "user", "content": prompt}],
                        )
                        return response.choices[0].message.content.strip()
                    except Exception as e:
                        logger.warning(f"Live points generation via Cerebras failed: {e}. Falling back to Groq...")

                # Fallback to Groq — log explicitly for production tracking
                if groq_client:
                    _now_rpm = time.time()
                    _groq_outline_call_times[:] = [t for t in _groq_outline_call_times if _now_rpm - t < 60]
                    if len(_groq_outline_call_times) >= _GROQ_OUTLINE_RPM_LIMIT:
                        logger.warning("⚠️ Groq outline suppressed — RPM ceiling approached")
                        return None
                    _groq_outline_call_times.append(_now_rpm)
                    try:
                        import datetime as _dt_fb
                        logger.warning(
                            f"🔄 Groq FALLBACK — live outline — {_dt_fb.datetime.now().strftime('%H:%M:%S')}"
                        )
                        response = groq_client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[{"role": "user", "content": prompt}],
                        )
                        return response.choices[0].message.content.strip()
                    except Exception as e:
                        logger.error(f"Live points generation via Groq fallback failed: {e}")

                return None

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, fetch_points)
            if result:
                LIVE_POINTS_CALLBACK(result)
        except Exception as e:
            logger.error(f"Live points loop execution error: {e}")


# ── SERMON SUMMARY  (Mistral → Cerebras → Groq) ──────────────────────────────
def generate_sermon_summary():
    global full_sermon_transcript, full_sermon_transcript_secondary, verses_cited, LLM_ENABLED
    global groq_client, cerebras_client, mistral_client

    if not LLM_ENABLED or (not mistral_client and not cerebras_client and not groq_client):
        return "⚠️ LLM disabled — add a Mistral, Cerebras, or Groq API key to generate summaries."

    if len(full_sermon_transcript.strip()) < 100:
        return "⚠️ Transcript is too short to generate a meaningful summary."

    import datetime
    today_str = datetime.datetime.now().strftime("%B %d, %Y  ·  %I:%M %p")

    verse_list = "\n".join([f"- {v}" for v in verses_cited]) if verses_cited else "None detected"

    # ── Dual-transcript prompt ──────────────────────────────────────────────
    has_secondary = bool(full_sermon_transcript_secondary.strip())
    if has_secondary:
        transcript_section = (
            f"PRIMARY TRANSCRIPT ({DEEPGRAM_LANGUAGE.upper() if not USE_SARVAM else 'Malayalam/translated'}):\n"
            f"{full_sermon_transcript}\n\n"
            f"SECONDARY TRANSCRIPT ({SECONDARY_LANGUAGE.upper() if SECONDARY_LANGUAGE else 'secondary'}):\n"
            f"{full_sermon_transcript_secondary}\n\n"
            "Both transcripts are from the SAME sermon captured by two parallel STT engines. "
            "Synthesize the most accurate notes by using the best of both transcripts — "
            "prefer whichever transcript has clearer verse references or speech for each section."
        )
    else:
        transcript_section = f"Transcript:\n{full_sermon_transcript}"

    prompt = (
        "You are a precise sermon note-taker. Your ONLY job is to document what was ACTUALLY SAID "
        "in the transcript below. You must NOT invent, infer, assume, or add anything that was not "
        "explicitly spoken by the preacher. If a section was not covered in the transcript, write "
        "'Not covered' — do not fill it in.\n\n"
        "STRICT RULES:\n"
        "1. Every point, quote, illustration, and application MUST come directly from the transcript.\n"
        "2. DO NOT generate questions, reflection prompts, or action steps unless the preacher explicitly stated them.\n"
        "3. DO NOT paraphrase beyond what is necessary for clarity — stay as close to the speaker's words as possible.\n"
        "4. If the transcript contains Malayalam, Hindi, or other languages, translate those portions to English.\n"
        "5. The verses listed below were detected by the system — use EXACTLY these references in the Verses Cited "
        "section. Do not add or remove any.\n\n"
        "Detected Verses (use these exactly):\n"
        f"{verse_list}\n\n"
        "Output the notes in this exact format:\n\n"
        "---\n"
        f"## 📅 {today_str}\n"
        "**Title:** [Title if stated, otherwise: Not mentioned]\n"
        "**Speaker:** [Name if stated, otherwise: Not mentioned]\n\n"
        "### 📖 Scripture\n"
        "**Main Passage:** [Primary passage if stated]\n\n"
        "### 💡 Main Message\n"
        "• [One sentence — the core point the preacher made, in their own words]\n\n"
        "### 📝 Points Covered\n"
        "[Bullet points — ONLY what the preacher explicitly stated. Each bullet is one clear idea from the sermon.]\n"
        "• \n"
        "• \n\n"
        "### 📖 Verses Cited\n"
        "[Copy the detected verses exactly as listed above]\n"
        "• \n\n"
        "### 🗣️ Notable Quotes & Illustrations\n"
        "[Direct quotes or stories the preacher used — only if they appear in the transcript]\n"
        "• \n"
        "---\n\n"
        f"{transcript_section}\n"
    )

    try:
        def fetch_summary():
            # 1. Try Mistral
            if mistral_client:
                try:
                    logger.info("⏳ Generating Summary via Mistral mistral-large-latest...")
                    r = mistral_client.chat.completions.create(
                        model="mistral-large-latest",
                        messages=[{"role": "user", "content": prompt}],
                    )
                    return r.choices[0].message.content.strip()
                except Exception as e:
                    logger.warning(f"Mistral summary failed: {e}")

            # 2. Try Cerebras
            if cerebras_client:
                try:
                    logger.info("⏳ Generating Summary via Cerebras gpt-oss-120b...")
                    r = cerebras_client.chat.completions.create(
                        model="gpt-oss-120b",
                        messages=[{"role": "user", "content": prompt}],
                    )
                    return r.choices[0].message.content.strip()
                except Exception as e:
                    logger.warning(f"Cerebras summary failed: {e}")

            # 3. Try Groq
            if groq_client:
                try:
                    logger.info("⏳ Generating Summary via Groq llama-3.3-70b-versatile...")
                    r = groq_client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": prompt}],
                    )
                    return r.choices[0].message.content.strip()
                except Exception as e:
                    logger.error(f"Groq summary failed: {e}")
            
            return None

        summary = fetch_summary()
        if not summary:
            return "⚠️ Summary failed: All LLM clients failed or none available."

        verse_str = "\n".join([f"- {v}" for v in verses_cited])
        if verse_str:
            summary += "\n\n### Verses Cited:\n" + verse_str

        logger.info("✅ Sermon Summary generated!")
        send_sermon_notes_to_discord(summary)
        return summary
    except Exception as e:
        logger.error(f"❌ Failed to generate summary: {e}")
        return f"Error generating summary: {e}"


def clear_sermon_buffer():
    global full_sermon_transcript, verses_cited
    full_sermon_transcript = ""
    verses_cited           = []
    _verse_history.clear()
    logger.info("🗑️ Sermon memory has been manually cleared.")


# ── ATEM KEYER TRIGGER ────────────────────────────────────────────────────────
# ── ATEM IP CACHE ─────────────────────────────────────────────────────────────
_atem_resolved_ip: str | None = None   # cached after first successful discovery

# ── ATEM CIRCUIT BREAKER ──────────────────────────────────────────────────────
_atem_fail_until: float = 0.0   # epoch time — skip keyer until this passes
_ATEM_BACKOFF_SECS = 60.0       # wait 60s after a connection failure before retrying

# Blackmagic Design MAC OUI prefixes (for ARP fallback)
_BMD_OUI = (
    "00:26:b0", "7c:2e:0d", "b4:fb:e4", "00:14:03",
    "28:c8:7a", "d4:20:b0", "b4:a9:fc", "00:17:f2",
    "ac:de:48",  # additional Blackmagic OUIs seen in the wild
)
_ATEM_CONTROL_PORT = 9910  # ATEM switchers listen on this TCP port


def _discover_atem_ip() -> str | None:
    """Try to find the ATEM's current IP automatically.
    1. mDNS/Bonjour — ATEM advertises _blackmagic._tcp on the LAN
    2. ARP scan      — look for Blackmagic Design MAC OUI on local subnet
    Returns the IP string or None if not found."""
    global _atem_resolved_ip

    # ── Strategy 1: mDNS (zeroconf) ──────────────────────────────────────────
    try:
        from zeroconf import Zeroconf, ServiceBrowser  # type: ignore
        import time as _t
        found_ip: list = []

        class _Listener:
            def add_service(self, zc, type_, name):
                info = zc.get_service_info(type_, name)
                if info and info.addresses:
                    import socket as _sock
                    ip = _sock.inet_ntoa(info.addresses[0])
                    found_ip.append(ip)
            def remove_service(self, *_): pass
            def update_service(self, *_): pass

        zc = Zeroconf()
        ServiceBrowser(zc, "_blackmagic._tcp.local.", _Listener())
        _t.sleep(2)   # give it 2s to respond
        zc.close()

        if found_ip:
            logger.info(f"🎬 ATEM discovered via mDNS: {found_ip[0]}")
            return found_ip[0]
    except ImportError:
        logger.debug("zeroconf not installed — skipping mDNS ATEM discovery")
    except Exception as e:
        logger.debug(f"mDNS ATEM discovery error: {e}")

    # ── Strategy 2: ARP table scan ────────────────────────────────────────────
    try:
        import subprocess as _sp, socket as _sock, re as _re
        result = _sp.run(["arp", "-a"], capture_output=True, text=True, timeout=5)
        for line in result.stdout.splitlines():
            mac_m = _re.search(r"([\da-f]{2}[:\-]){5}[\da-f]{2}", line, _re.IGNORECASE)
            ip_m  = _re.search(r"(\d{1,3}(?:\.\d{1,3}){3})", line)
            if mac_m and ip_m:
                mac = mac_m.group(0).lower().replace("-", ":")
                if any(mac.startswith(oui) for oui in _BMD_OUI):
                    ip = ip_m.group(1)
                    logger.info(f"🎬 ATEM discovered via ARP: {ip} (MAC {mac})")
                    return ip
    except Exception as e:
        logger.debug(f"ARP ATEM discovery error: {e}")

    # ── Strategy 3: Port 9910 subnet scan ───────────────────────────────────
    # ATEM switchers always listen on TCP 9910. Scan every host on the local
    # subnet(s) with a short timeout. Skips loopback and link-local ranges.
    try:
        import socket as _sock, ipaddress as _ipa, concurrent.futures as _cf
        import time as _t

        # Collect local subnet prefixes from all non-loopback interfaces
        local_prefixes: list = []
        try:
            import netifaces as _ni  # type: ignore
            for iface in _ni.interfaces():
                addrs = _ni.ifaddresses(iface).get(_ni.AF_INET, [])
                for a in addrs:
                    ip_s  = a.get("addr", "")
                    mask  = a.get("netmask", "")
                    if ip_s and mask and not ip_s.startswith("127.") and not ip_s.startswith("169."):
                        try:
                            net = _ipa.IPv4Network(f"{ip_s}/{mask}", strict=False)
                            if net.num_addresses <= 512:   # only scan /23 or smaller
                                local_prefixes.append(str(net))
                        except Exception:
                            pass
        except ImportError:
            pass

        # Fallback: derive subnet from default gateway route
        if not local_prefixes:
            try:
                s = _sock.socket(_sock.AF_INET, _sock.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                my_ip = s.getsockname()[0]
                s.close()
                parts = my_ip.rsplit(".", 1)
                local_prefixes.append(f"{parts[0]}.0/24")
            except Exception:
                pass

        def _probe(host: str) -> str | None:
            try:
                s = _sock.socket(_sock.AF_INET, _sock.SOCK_STREAM)
                s.settimeout(0.25)
                result = s.connect_ex((host, _ATEM_CONTROL_PORT))
                s.close()
                if result == 0:
                    return host
            except Exception:
                pass
            return None

        for prefix in local_prefixes:
            hosts = [str(h) for h in _ipa.IPv4Network(prefix, strict=False).hosts()]
            logger.info(f"🎬 ATEM port scan: checking {len(hosts)} hosts on {prefix}...")
            with _cf.ThreadPoolExecutor(max_workers=80) as ex:
                results = list(ex.map(_probe, hosts))
            hits = [r for r in results if r]
            if hits:
                ip = hits[0]
                logger.info(f"🎬 ATEM discovered via port scan: {ip}")
                return ip

    except Exception as e:
        logger.debug(f"Port-scan ATEM discovery error: {e}")

    return None


def _resolve_atem_ip() -> str | None:
    """Return the ATEM IP to use.
    - If ATEM_IP is set to a real IP → use it directly.
    - If ATEM_IP is blank, 'auto', or '0.0.0.0' → auto-discover.
    Caches the result so discovery only runs once per session."""
    global _atem_resolved_ip

    # Already resolved this session
    if _atem_resolved_ip:
        return _atem_resolved_ip

    manual = ATEM_IP.strip().lower()
    if manual and manual not in ("", "auto", "0.0.0.0"):
        _atem_resolved_ip = ATEM_IP.strip()
        return _atem_resolved_ip

    # Auto-discover
    logger.info("🎬 ATEM IP set to Auto — scanning network...")
    ip = _discover_atem_ip()
    if ip:
        _atem_resolved_ip = ip
    else:
        logger.warning("⚠️ ATEM auto-discovery failed — keyer will be skipped")
    return _atem_resolved_ip


def _trigger_atem_keyer():
    """Fire upstream keyer 1 ON for ATEM_KEY_DURATION seconds, then OFF.
    Resolves the ATEM IP automatically if not hardcoded.
    Runs entirely in a daemon thread — never blocks verse delivery."""
    if not ATEM_ENABLED:
        return

    def _run():
        global _atem_fail_until
        import time as _t

        # Circuit breaker — skip if we failed recently
        if _t.time() < _atem_fail_until:
            logger.debug(f"🎬 ATEM: skipped (circuit open, retrying in {int(_atem_fail_until - _t.time())}s)")
            return

        ip = _resolve_atem_ip()
        if not ip:
            logger.warning("⚠️ ATEM: no IP available — keyer skipped")
            return
        try:
            import PyATEMMax  # type: ignore
            sw = PyATEMMax.ATEMMax()
            sw.connect(ip)
            _t.sleep(2)          # wait for data exchange
            sw.setKeyerOnAirEnabled(0, 0, True)
            logger.info(f"🎬 ATEM: keyer ON  ({ip})")
            _t.sleep(ATEM_KEY_DURATION)
            sw.setKeyerOnAirEnabled(0, 0, False)
            logger.info(f"🎬 ATEM: keyer OFF (was on for {ATEM_KEY_DURATION}s)")
            _t.sleep(0.5)
            sw.disconnect()
            _atem_fail_until = 0.0  # reset on success
        except ImportError:
            logger.warning("⚠️ PyATEMMax not installed — pip install PyATEMMax")
        except Exception as e:
            _atem_fail_until = _t.time() + _ATEM_BACKOFF_SECS
            logger.warning(f"⚠️ ATEM error: {e} — pausing keyer for {int(_ATEM_BACKOFF_SECS)}s")

    threading.Thread(target=_run, daemon=True).start()


# ── CONFIGURE ────────────────────────────────────────────────────────────────
def configure(
    language="en", mic_index=1, rate=16000, chunk=4096,
    remote_url="http://localhost:50010/control.html",
    dedup_window=60, cooldown=3.0, llm_enabled=True,
    bible_translation="kjv", deepgram_api_key="",
    groq_api_key="", gemini_api_key="", cerebras_api_key="",
    mistral_api_key="", sarvam_api_key="",
    discord_webhook_url="", discord_log_webhook_url="", discord_notes_webhook_url="",
    confidence=0.75, manual_confirm=True,
    confirm_callback=None, verify=True, verse_interrupt=False,
    spoken_numeral_mode=False, worship_mode=False,
    panic_key="esc", smart_amen=True,
    live_points_prompt="", live_points_callback=None, live_points_get_current_cb=None,
    live_points_enabled=False, silence_timeout=60,
    atem_enabled=False, atem_ip="192.168.1.240", atem_key_duration=5.0,
    gui_app=None,
    bridge_ready_callback=None,
    dual_stt_enabled=False, secondary_language=None, secondary_stt_engine="deepgram",
    assemblyai_api_key="", stt_engine="deepgram",
    aai_turn_cutoff=5,
    malayalam_transliteration=False,
):
    global DEEPGRAM_API_KEY, GROQ_API_KEY, GEMINI_API_KEY, CEREBRAS_API_KEY, MISTRAL_API_KEY, SARVAM_API_KEY
    global DISCORD_WEBHOOK_URL, DISCORD_LOG_WEBHOOK_URL, DISCORD_NOTES_WEBHOOK_URL
    global USE_SARVAM, DEEPGRAM_LANGUAGE, DEEPGRAM_MODEL, SARVAM_LANGUAGE
    global PRIMARY_PARSER, MIC_INDEX, RATE, CHUNK, REMOTE_URL
    global show_malayalam_raw, MALAYALAM_TRANSLITERATION
    global DEDUP_WINDOW, COOLDOWN, LLM_ENABLED, BIBLE_TRANSLATION, USE_XPATH
    global groq_client, cerebras_client, mistral_client
    global CONFIDENCE_THRESHOLD, REQUIRE_MANUAL_CONFIRM, CONFIRM_CALLBACK, REQUIRE_VERIFY, PANIC_KEY, SMART_AMEN_ENABLED
    global full_sermon_transcript, verses_cited
    global LIVE_POINTS_PROMPT, LIVE_POINTS_CALLBACK, LIVE_POINTS_GET_CURRENT_CB
    global LIVE_POINTS_ENABLED, SILENCE_TIMEOUT
    global normalize_numbers_only
    global VERSE_INTERRUPT_ENABLED, SPOKEN_NUMERAL_MODE, WORSHIP_MODE, _verse_history
    global ATEM_ENABLED, ATEM_IP, ATEM_KEY_DURATION
    global current_book, current_chapter, current_verse, _gui_app
    global BRIDGE_READY_CALLBACK
    global _sermon_anchor_book, _sermon_anchor_chapter, _sermon_anchor_verse
    global _xref_anchor_book, _xref_anchor_chapter, _xref_anchor_verse, _xref_anchor_time
    global DUAL_STT_ENABLED, SECONDARY_LANGUAGE, SECONDARY_PARSER
    global SECONDARY_DEEPGRAM_LANGUAGE, SECONDARY_DEEPGRAM_MODEL, SECONDARY_USE_SARVAM
    global _force_stopped
    _force_stopped = False
    global SECONDARY_STT_ENGINE
    global full_sermon_transcript_secondary
    global ASSEMBLYAI_API_KEY, STT_ENGINE, AAI_LANGUAGE, AAI_TURN_CUTOFF_SEC
    WORSHIP_MODE = False
    _exit_scripture_read_mode(reason="session-reset")
    if not _verse_history:          # only wipe on a true fresh launch
        _verse_history.clear()
    # Reset context so stale chapter from previous session never bleeds in
    current_book    = None
    current_chapter = None
    current_verse   = None
    _sermon_anchor_book    = None
    _sermon_anchor_chapter = None
    _sermon_anchor_verse   = None
    _xref_anchor_book    = None
    _xref_anchor_chapter = None
    _xref_anchor_verse   = None
    _xref_anchor_time    = 0.0
    _gui_app               = gui_app
    BRIDGE_READY_CALLBACK  = bridge_ready_callback
    logger.info("📌 Context reset for new session")
    _cancel_vtc()

    # Reset Discord live log and session log stream for fresh session
    _discord_live_log.reset()
    session_log_stream.truncate(0)
    session_log_stream.seek(0)

    # NOTE: Sermon buffer is intentionally NOT reset here so memory persists across stops/starts!
    global _llm_in_flight
    _llm_in_flight = False
    # BUG 2: Reset shutdown flag and thread registry so new session starts clean
    _shutdown_flag.clear()
    _active_bg_threads.clear()
    # Hard confirmation gate: clear any pending-verse hints from a previous session
    global _gate_pending
    _gate_pending.clear()
    # Quarantine: reset so a fresh session starts clean
    global _manual_context_set_time, _quarantine_transcript_offset
    _manual_context_set_time        = 0.0
    _quarantine_transcript_offset   = 0

    DEEPGRAM_API_KEY = deepgram_api_key
    GROQ_API_KEY     = groq_api_key
    GEMINI_API_KEY   = gemini_api_key
    CEREBRAS_API_KEY = cerebras_api_key
    MISTRAL_API_KEY  = mistral_api_key
    SARVAM_API_KEY   = sarvam_api_key
    ASSEMBLYAI_API_KEY = assemblyai_api_key
    # Normalize "assemblyai_pro" / "assemblyai_multilingual" → "assemblyai" so
    # main() STT_ENGINE == "assemblyai" branches always match.  The model variant
    # is conveyed via AAI_LANGUAGE: "multi" → universal-streaming-multilingual,
    # else → u3-rt-pro (set below in the language routing block).
    _raw_engine = stt_engine.lower().strip() if stt_engine else "deepgram"
    STT_ENGINE  = "assemblyai" if _raw_engine.startswith("assemblyai") else _raw_engine
    _primary_aai_multilingual = (_raw_engine == "assemblyai_multilingual")
    AAI_TURN_CUTOFF_SEC = max(3, min(11, int(aai_turn_cutoff or 5)))
    MALAYALAM_TRANSLITERATION = malayalam_transliteration

    # ── Groq: verse extraction only ──
    groq_client = _GroqClient(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
    if groq_client:
        logger.info("🔍 Verse LLM          : Groq  llama-3.1-8b-instant")
    else:
        logger.warning("⚠️  No Groq key — LLM verse extraction disabled")

    # ── Cerebras: live outline + summary fallback ──
    cerebras_client = _CerebrasClient(api_key=CEREBRAS_API_KEY) if CEREBRAS_API_KEY else None
    if cerebras_client:
        logger.info("📋 Live Outline LLM   : Cerebras  gpt-oss-120b")
        # Bug 1: startup validation ping — runs in background to catch model errors early
        def _validate_cerebras():
            try:
                import requests as _req, certifi as _cert
                resp = _req.post(
                    "https://api.cerebras.ai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {CEREBRAS_API_KEY}", "Content-Type": "application/json"},
                    json={"model": "llama3.1-8b", "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1},
                    timeout=15, verify=_cert.where(),
                )
                if resp.status_code == 200:
                    logger.info("✅ Cerebras startup ping OK — gpt-oss-120b responsive")
                elif resp.status_code == 404:
                    logger.error("❌ Cerebras startup ping FAILED: model 'gpt-oss-120b' not found (404)")
                else:
                    logger.warning(f"⚠️ Cerebras startup ping returned status {resp.status_code}")
            except Exception as e:
                logger.error(f"❌ Cerebras startup validation error: {e}")
        threading.Thread(target=_validate_cerebras, daemon=True).start()

    # ── Mistral: sermon summary primary ──
    mistral_client = _MistralClient(api_key=MISTRAL_API_KEY) if MISTRAL_API_KEY else None
    if mistral_client:
        logger.info("✍️  Sermon Summary LLM : Mistral  mistral-large-latest")
    elif cerebras_client:
        logger.info("✍️  Sermon Summary LLM : Cerebras  gpt-oss-120b  (no Mistral key)")
    elif groq_client:
        logger.info("✍️  Sermon Summary LLM : Groq  llama-3.3-70b-versatile  (no Mistral/Cerebras key)")
    else:
        logger.warning("⚠️  No LLM keys at all — all LLM features disabled")

    DISCORD_WEBHOOK_URL       = discord_webhook_url
    DISCORD_LOG_WEBHOOK_URL   = discord_log_webhook_url
    DISCORD_NOTES_WEBHOOK_URL = discord_notes_webhook_url

    USE_XPATH         = sys.platform == "darwin"
    MIC_INDEX         = mic_index
    RATE              = rate
    CHUNK             = chunk
    REMOTE_URL        = remote_url
    if not REMOTE_URL.startswith(("http://", "https://")):
        logger.warning(f"⚠️ Invalid VerseView URL '{REMOTE_URL}' — resetting to default.")
        REMOTE_URL = "http://localhost:50010/control.html"
    DEDUP_WINDOW      = dedup_window
    COOLDOWN          = cooldown
    LLM_ENABLED       = llm_enabled
    BIBLE_TRANSLATION = bible_translation

    CONFIDENCE_THRESHOLD   = confidence
    REQUIRE_MANUAL_CONFIRM = manual_confirm
    CONFIRM_CALLBACK       = confirm_callback
    REQUIRE_VERIFY         = verify
    PANIC_KEY              = panic_key
    SMART_AMEN_ENABLED     = smart_amen
    VERSE_INTERRUPT_ENABLED  = verse_interrupt
    SPOKEN_NUMERAL_MODE      = spoken_numeral_mode
    WORSHIP_MODE             = worship_mode
    logger.info(f"🎸 Worship Mode       : {'ON' if WORSHIP_MODE else 'OFF'}")
    logger.info(f"📖 Scripture-Read Mode: {'ON' if SCRIPTURE_READ_MODE else 'STANDBY (auto-triggered by speech)'}")
    # ── Discord: citations ──
    set_spoken_numeral_mode(spoken_numeral_mode)
    logger.info(f"🔣 Spoken Numeral Mode: {'ON' if spoken_numeral_mode else 'OFF'}")
    LIVE_POINTS_PROMPT         = live_points_prompt
    LIVE_POINTS_CALLBACK       = live_points_callback
    LIVE_POINTS_GET_CURRENT_CB = live_points_get_current_cb
    LIVE_POINTS_ENABLED        = live_points_enabled
    SILENCE_TIMEOUT            = silence_timeout
    logger.info(f"📋 Live Points: {'ON' if LIVE_POINTS_ENABLED else 'OFF'}")

    ATEM_ENABLED      = atem_enabled
    ATEM_IP           = atem_ip
    ATEM_KEY_DURATION = atem_key_duration
    global _atem_resolved_ip
    _atem_resolved_ip = None  # clear cache so IP is re-resolved each session
    global _atem_fail_until
    _atem_fail_until = 0.0    # reset circuit breaker
    if ATEM_ENABLED:
        logger.info(f"🎬 ATEM Overlay        : ON  ({ATEM_IP or 'Auto'}, key on for {ATEM_KEY_DURATION}s)")

    if language == "en":
        USE_SARVAM             = False
        DEEPGRAM_LANGUAGE      = "en"
        DEEPGRAM_MODEL         = "nova-3"
        PRIMARY_PARSER         = parse_eng
        normalize_numbers_only = norm_eng
        # Use "multi" model when the user chose the Multilingual dropdown option
        AAI_LANGUAGE           = "multi" if _primary_aai_multilingual else "en"
    elif language == "hi":
        USE_SARVAM             = False
        DEEPGRAM_LANGUAGE      = "hi"
        DEEPGRAM_MODEL         = "nova-3"
        PRIMARY_PARSER         = parse_hindi
        normalize_numbers_only = norm_hindi
        AAI_LANGUAGE           = "hi"
    elif language == "ml":
        USE_SARVAM             = True
        SARVAM_LANGUAGE        = "ml-IN"
        # Must use parse_ml here — parse_eng strips all non-ASCII chars and
        # therefore destroys every Malayalam character before matching. parse_ml
        # handles both Malayalam book names AND English code-switching (e.g.
        # "ജോൺ ചാപ്റ്റർ 12:27" or "John chapter 12 verse 5").
        PRIMARY_PARSER         = parse_ml
        normalize_numbers_only = norm_ml
        AAI_LANGUAGE           = "ml"
    else:
        USE_SARVAM             = False
        DEEPGRAM_LANGUAGE      = "multi"
        DEEPGRAM_MODEL         = "nova-3"
        PRIMARY_PARSER         = parse_eng
        normalize_numbers_only = norm_eng
        AAI_LANGUAGE           = "multi"

    # ── Dual STT — secondary stream configuration ──
    DUAL_STT_ENABLED   = dual_stt_enabled
    SECONDARY_LANGUAGE = secondary_language
    SECONDARY_STT_ENGINE = secondary_stt_engine
    full_sermon_transcript_secondary = ""
    if dual_stt_enabled and secondary_language:
        # Set parser based on secondary language
        if secondary_language == "en":
            SECONDARY_DEEPGRAM_LANGUAGE = "en"
            SECONDARY_DEEPGRAM_MODEL    = "nova-3"
            SECONDARY_PARSER            = parse_eng
        elif secondary_language == "hi":
            SECONDARY_DEEPGRAM_LANGUAGE = "hi"
            SECONDARY_DEEPGRAM_MODEL    = "nova-3"
            SECONDARY_PARSER            = parse_hindi
        elif secondary_language == "ml":
            SECONDARY_DEEPGRAM_LANGUAGE = "en"   # unused when Sarvam/AAI handles ml
            SECONDARY_DEEPGRAM_MODEL    = "nova-3"
            SECONDARY_PARSER            = parse_ml
        else:
            SECONDARY_DEEPGRAM_LANGUAGE = "multi"
            SECONDARY_DEEPGRAM_MODEL    = "nova-3"
            SECONDARY_PARSER            = parse_eng

        # Route secondary stream: Sarvam only for ml+sarvam, AAI for any assemblyai* code, else Deepgram
        # Normalize "assemblyai_pro" / "assemblyai_multilingual" → "assemblyai" so
        # main()'s SECONDARY_STT_ENGINE == "assemblyai" check always matches.
        _raw_sec = secondary_stt_engine.lower().strip() if secondary_stt_engine else "deepgram"
        SECONDARY_STT_ENGINE = "assemblyai" if _raw_sec.startswith("assemblyai") else _raw_sec
        SECONDARY_USE_SARVAM = (secondary_language == "ml" and _raw_sec == "sarvam")

        logger.info(f"🌐 Dual STT          : ON  (secondary={secondary_language}, engine={secondary_stt_engine})")
    else:
        SECONDARY_USE_SARVAM = False
        SECONDARY_STT_ENGINE = "deepgram"
        SECONDARY_PARSER     = None


# ── CONTEXT TRACKING ─────────────────────────────────────────────────────────
current_book    = None
current_chapter = None
current_verse   = None

# ── SERMON ANCHOR vs CROSS-REFERENCE ANCHOR ───────────────────────────────────
# _sermon_anchor_* is the stable main-passage context.  It is only updated when
# the speaker demonstrably *moves* the sermon to a new book+chapter (different
# book, or same book but chapter change while no xref is active).
#
# _xref_anchor_* is a short-lived overlay set when an explicit cross-reference
# lands in a *different* book than the sermon anchor.  Contextual phrases like
# "verse nine" prefer the sermon anchor while a xref is active so they resolve
# against the main passage, not the cross-reference.
#
# After _XREF_ANCHOR_TTL seconds without another explicit xref, the overlay
# expires and contextual resolution reverts to current_book/current_chapter as
# normal (which will have been restored to the sermon anchor by then).
_XREF_ANCHOR_TTL: float    = 120.0   # seconds a cross-ref anchor stays valid

_sermon_anchor_book:    str = None
_sermon_anchor_chapter: str = None
_sermon_anchor_verse:   str = None

_xref_anchor_book:    str   = None
_xref_anchor_chapter: str   = None
_xref_anchor_verse:   str   = None
_xref_anchor_time:    float = 0.0   # time.time() when xref anchor was last set

_gui_app               = None   # injected by configure(); used by bot bridge for GUI refresh
BRIDGE_READY_CALLBACK  = None   # called once the bot bridge starts successfully



def get_context() -> dict:
    return {"book": current_book or "", "chapter": current_chapter or "", "verse": current_verse or ""}


# ── SYSTEM-ACTION QUARANTINE HELPERS ─────────────────────────────────────────

def _open_system_quarantine(reason: str) -> None:
    """Open the quarantine window.

    Called by set_context(), restore_session_snapshot(), and
    add_to_verse_history() for system-sourced events.  While the
    quarantine is active, deliver_verse() blocks all inferred detections
    (CONTEXTUAL, SEQUENTIAL, LLM, RANGE, READ-INTENT, PARSER, SIMPLE)
    until fresh spoken evidence arrives.

    Does NOT affect FAST-PATH, TRANSLATION-PATH, QUEUE, NEXT VERSE, or
    ONWARDS — those carry their own evidence of explicit speech.
    """
    global _manual_context_set_time, _quarantine_transcript_offset
    _manual_context_set_time      = time.time()
    _quarantine_transcript_offset = len(full_sermon_transcript)
    logger.info(
        f"🔒 QUARANTINE OPENED ({reason}) — inferred detections suppressed "
        f"until {_MANUAL_CONTEXT_BYPASS_WINDOW:.0f}s elapses or "
        f"≥{_QUARANTINE_MIN_NEW_CHARS} chars of fresh spoken evidence arrive"
    )


def _in_system_quarantine(text: str) -> bool:
    """Return True when the quarantine is active AND the transcript has not
    yet accumulated enough fresh spoken content to clear it early.

    Early-clear rules (any one is sufficient):
      1. An explicit full reference (book + chapter + verse) appears in
         *text* — the speaker clearly said something unambiguous.
      2. The sermon transcript has grown by ≥ _QUARANTINE_MIN_NEW_CHARS
         characters since the quarantine opened, AND the new tail contains
         a verse-keyword signal ("verse N", "N:N" colon notation, etc.).

    If the quarantine window has simply expired (_MANUAL_CONTEXT_BYPASS_WINDOW
    seconds), we also return False (quarantine over).
    """
    if not CONTEXT_FLOOR_MANUAL_CONTEXT_BYPASS:
        return False          # feature disabled
    if _manual_context_set_time == 0.0:
        return False          # never opened

    age = time.time() - _manual_context_set_time
    if age >= _MANUAL_CONTEXT_BYPASS_WINDOW:
        return False          # expired naturally

    # Early-clear check 1: explicit full ref in current transcript chunk
    if _is_explicit_full_ref(text):
        logger.info(
            f"✅ QUARANTINE CLEARED EARLY — explicit full ref found in transcript "
            f"(age={age:.1f}s)"
        )
        return False

    # Early-clear check 2: enough new spoken text with a verse signal
    new_chars = len(full_sermon_transcript) - _quarantine_transcript_offset
    if new_chars >= _QUARANTINE_MIN_NEW_CHARS:
        # Look for a verse signal in the most-recent portion of the transcript
        tail = full_sermon_transcript[-max(new_chars, 120):]
        _VERSE_SIGNAL_RE = re.compile(
            r'(?:'
            r'\b[A-Za-z]\w*\s+\d{1,3}:\d{1,3}\b'           # colon notation
            r'|'
            r'\bverse[s]?\s+\d+'                             # "verse N"
            r'|'
            r'\b(?:chapter|chap|ch)\s+\d+\s+verse\s+\d+'    # spoken form
            r'|'
            r'[\u0D66-\u0D6F]+'                              # Malayalam digits
            r'|'
            r'[\u0966-\u096F]+'                              # Devanagari digits
            r')',
            re.IGNORECASE,
        )
        if _VERSE_SIGNAL_RE.search(tail):
            logger.info(
                f"✅ QUARANTINE CLEARED EARLY — {new_chars} new chars + verse "
                f"signal in transcript tail (age={age:.1f}s)"
            )
            return False

    # Still in quarantine
    logger.debug(
        f"🔒 QUARANTINE ACTIVE — age={age:.1f}s, "
        f"new_chars={len(full_sermon_transcript) - _quarantine_transcript_offset}"
    )
    return True


def set_context(book: str, chapter: str, verse: str):
    """Update current sermon context.

    Validation rules (Issue A fix)
    ──────────────────────────────
    • book and chapter are required; a call with either missing is rejected so
      state never contains a half-formed ref like "1 Chronicles 4None".
    • verse may be absent (chapter-only context is valid).  When absent we store
      None explicitly — never the string "None" or an empty string in a verse slot.
    • chapter must look like a plain integer string (e.g. "4", not "4:9").
    • If validation fails the existing state is left unchanged.
    """
    global current_book, current_chapter, current_verse
    global _manual_context_set_time, _last_presented_verse_num, _last_presented_verse_book_chap
    global _sermon_anchor_book, _sermon_anchor_chapter, _sermon_anchor_verse
    global _xref_anchor_book, _xref_anchor_chapter, _xref_anchor_verse, _xref_anchor_time

    # ── Normalise inputs ──────────────────────────────────────────────────────
    _book    = (book    or "").strip()
    _chapter = (chapter or "").strip()
    _verse   = (verse   or "").strip()

    # Treat the string literal "None" as absent (guards against Python str(None))
    if _verse.lower() == "none":
        _verse = ""

    # ── Validate required fields ──────────────────────────────────────────────
    if not _book:
        logger.warning("⛔ set_context rejected: book is empty — state unchanged")
        return
    if not _chapter:
        logger.warning(
            f"⛔ set_context rejected: chapter is empty for book '{_book}' — state unchanged"
        )
        return
    # chapter must be a bare integer string; a colon indicates the caller has
    # accidentally passed a "chapter:verse" blob into the chapter slot.
    if not _chapter.isdigit():
        logger.warning(
            f"⛔ set_context rejected: chapter '{_chapter}' for '{_book}' is not a "
            f"plain integer — state unchanged (possible 'chapter:verse' in wrong slot)"
        )
        return
    # If a verse was provided it must also be a bare integer string.
    if _verse and not _verse.isdigit():
        logger.warning(
            f"⛔ set_context rejected: verse '{_verse}' for '{_book} {_chapter}' is not "
            f"a plain integer — storing chapter-only context instead"
        )
        _verse = ""

    # ── Commit validated state ────────────────────────────────────────────────
    current_book    = _book
    current_chapter = _chapter
    current_verse   = _verse or None   # chapter-only → explicit None, never ""

    # Manual context set is always treated as a sermon anchor update —
    # it represents intentional operator action, never a cross-reference.
    _sermon_anchor_book    = current_book
    _sermon_anchor_chapter = current_chapter
    _sermon_anchor_verse   = current_verse
    # Clear any stale xref overlay
    _xref_anchor_book    = None
    _xref_anchor_chapter = None
    _xref_anchor_verse   = None
    _xref_anchor_time    = 0.0

    # Reset the contextual floor so it is relative to the new manual position,
    # not whatever verse was last auto-presented.  If the caller sets Daniel 11:5,
    # contextual detections like "verse 3" should be evaluated against v5, not an
    # older presented verse from a different part of the sermon.
    if current_verse:
        _new_key = f"{current_book} {current_chapter}"
        try:
            _last_presented_verse_num       = int(current_verse)
            _last_presented_verse_book_chap = _new_key
        except (ValueError, TypeError):
            pass

    # Open a quarantine window: manual context is metadata only.
    # Inferred detections are suppressed until fresh spoken evidence arrives.
    _open_system_quarantine("set_context")

    # Build a display ref that is never malformed ("Book Ch" or "Book Ch:V")
    _display_ref = (
        f"{current_book} {current_chapter}:{current_verse}"
        if current_verse
        else f"{current_book} {current_chapter} (chapter-only)"
    )
    logger.info(
        f"📌 Context manually set: {_display_ref} "
        f"— inferred detections quarantined for up to "
        f"{_MANUAL_CONTEXT_BYPASS_WINDOW:.0f}s (metadata only; spoken evidence required)"
    )


# ── VERSE RANGE QUEUE ─────────────────────────────────────────────────────────
verse_queue      = []
verse_queue_lock = threading.Lock()

RANGE_RE = re.compile(
    r'(?P<start>\d+)\s*(?:through|thru|to|and|ending\s+at|-|–)\s*(?P<end>\d+)',
    re.IGNORECASE | re.VERBOSE,
)

BOOK_KEYWORDS = (
    "genesis,exodus,leviticus,numbers,deuteronomy,"
    "joshua,judges,ruth,samuel,kings,chronicles,"
    "ezra,nehemiah,esther,job,psalm,psalms,"
    "proverbs,ecclesiastes,isaiah,jeremiah,"
    "lamentations,ezekiel,daniel,hosea,joel,"
    "amos,obadiah,jonah,micah,nahum,habakkuk,"
    "zephaniah,haggai,zechariah,malachi,"
    "matthew,mark,luke,john,acts,romans,"
    "corinthians,galatians,ephesians,philippians,"
    "colossians,thessalonians,timothy,titus,"
    "philemon,hebrews,james,peter,jude,revelation"
).split(",")

NUMBER_WORDS = (
    "one,two,three,four,five,six,seven,eight,"
    "nine,ten,eleven,twelve,thirteen,fourteen,fifteen,"
    "sixteen,seventeen,eighteen,nineteen,twenty,thirty,"
    "forty,fifty,sixty,seventy,eighty,ninety,hundred"
).split(",")


# ── BIBLE FETCH ───────────────────────────────────────────────────────────────
def fetch_verse_text(ref: str) -> str | None:
    text = multi_fetch(ref, BIBLE_TRANSLATION)
    if text:
        return text
    logger.warning(f"All APIs failed for {ref}")
    logger.debug(f"Failed to fetch verse text for {ref}. Trying to understand why the fourth call fails.")
    return None


# ── VERSE INTERRUPT (wait for speaker to say verse, then display; 60s timeout; cancel on new ref) ─
def deliver_verse(ref: str, controller, bypass_cooldown=False, confidence=1.0, source="UNKNOWN"):
    """
    Deliver a detected verse: if Verse Interrupt is on, wait for the speaker to say the verse
    (fetch text via Bible API, listen for trigger words, 60s timeout; new ref cancels current).
    Otherwise send directly to controller.

    ── HARD CONFIRMATION GATE ────────────────────────────────────────────────
    A verse is presented ONLY when one of these conditions is satisfied:

      A) Source is FAST-PATH or TRANSLATION-PATH
            → The parser found an explicit book + chapter + verse in the
              transcript.  These paths already require colon notation or
              full spoken form; no guessing involved.

      B) The system is in ONWARDS mode (locked sequential verse-reading)
            → The preacher is working through a passage verse-by-verse.
              The next verse is the only valid continuation, so no
              confirmation window is needed.

      C) Source is QUEUE or NEXT VERSE
            → The verse was already confirmed and queued during a range
              announcement.  No re-confirmation needed.

      D) The same reference has been independently detected ≥2 times
         within _GATE_WINDOW_SECS seconds
            → Two independent hits from the layered detectors (parser,
              contextual, sequential, LLM, etc.) arriving in a short
              window constitutes strong corroboration.

    ALL other detections — including single-hit PARSER, CONTEXTUAL,
    SEQUENTIAL, READ-INTENT, RANGE, LLM — are held on the first
    occurrence.  No verse is guessed, no nearby verse is substituted.
    Prefer silence over a wrong presentation.

    ── SYSTEM-ACTION QUARANTINE ─────────────────────────────────────────────
    When a manual context change, chapter-browser click, history injection,
    or session restore has recently occurred, a quarantine window is active.
    During that window all inferred detections (conditions B/D above) are
    additionally suppressed until fresh spoken evidence clears the quarantine.
    Sources that carry explicit spoken evidence (A, plus any bypass_cooldown
    path) are NOT affected by the quarantine.
    ──────────────────────────────────────────────────────────────────────────
    """
    global _gate_pending

    # ── SCRIPTURE-READ MODE GATE ──────────────────────────────────────────────
    # While SCRIPTURE-READ is active, only verses within the locked passage
    # are allowed.  Verses in a different book or chapter, or too far outside
    # the expected sequential position, are silently dropped so that sermon
    # numbers, timestamps, and paraphrase fragments never reach the display.
    # Explicitly-parsed FAST-PATH refs in the same passage always pass through.
    if SCRIPTURE_READ_MODE and not _scripture_read_verse_allowed(ref):
        logger.info(f"📖 SR-GATE BLOCKED: {ref} [{source}] — outside locked passage "
                    f"({_sr_locked_book} {_sr_locked_chapter}, expected v{_sr_expected_verse})")
        _gate_pending.pop(ref, None)
        return

    # ── GATE CONDITIONS A / B / C: always pass through ──
    # LLM added to bypass — the LLM path now has its own internal guards
    # (anchor-match suppression + hardened prompt + paraphrase-content guard)
    # so the external gate withholding is no longer needed.
    _BYPASS_SOURCES = {"FAST-PATH", "TRANSLATION-PATH", "QUEUE", "NEXT VERSE", "LLM"}
    if source in _BYPASS_SOURCES or bypass_cooldown:
        # Condition A / C: explicit ref already verified upstream, or range/queue continuation
        # Condition B: bypass_cooldown=True is also set by ONWARDS in controller.send_verse
        # ── SCRIPTURE-READ: advance expected verse pointer ──────────────────
        if SCRIPTURE_READ_MODE and ":" in ref:
            try:
                _v = int(ref.rsplit(":", 1)[1])
                scripture_read_advance_expected(_v)
                # Exit SR mode if a clear new anchor in a DIFFERENT chapter arrives
                ref_chapter = ref.rsplit(":", 1)[0].split()[-1]
                if _sr_locked_chapter and ref_chapter != _sr_locked_chapter:
                    _exit_scripture_read_mode(reason="new-chapter-anchor")
            except (ValueError, IndexError):
                pass
        if VERSE_INTERRUPT_ENABLED:
            _start_vtc(ref, controller, source=source)
        else:
            controller.send_verse(ref, bypass_cooldown=bypass_cooldown, confidence=confidence, source=source)
        return

    # ── SYSTEM-ACTION QUARANTINE CHECK ──
    # When a manual context change, chapter-browser click, history injection,
    # or session restore has recently occurred, a quarantine window is active.
    # During that window all *inferred* detections are suppressed unless fresh
    # spoken evidence arrives.
    if _in_system_quarantine(ref if ref else ""):
        logger.info(
            f"🔒 QUARANTINE BLOCKED inferred detection: {ref} [{source}] — "
            f"waiting for fresh spoken evidence after system action"
        )
        return

    # ── INFERRED DETECTIONS: pass straight through ──
    # The hard confirmation gate has been removed.  When the engine hears a
    # verse via PARSER, CONTEXTUAL, SEQUENTIAL, RANGE, READ-INTENT, or LLM,
    # it now passes directly to the display — no 45-second withholding window,
    # no "hear twice" requirement.  The individual detection layers have their
    # own guards (e.g. the LLM path has anchor-match suppression + prompt
    # hardening).  This makes the engine responsive: when the preacher says a
    # verse, it shows immediately.
    if SCRIPTURE_READ_MODE and ":" in ref:
        try:
            scripture_read_advance_expected(int(ref.rsplit(":", 1)[1]))
        except (ValueError, IndexError):
            pass
    if VERSE_INTERRUPT_ENABLED:
        _start_vtc(ref, controller, source=source)
    else:
        controller.send_verse(ref, bypass_cooldown=bypass_cooldown, confidence=confidence, source=source)


def get_verse_history() -> list:
    return list(_verse_history)


def force_stop() -> None:
    """Immediate, no-cleanup stop of the STT engine loop.
    Sets stop_event just like request_stop(), but also sets a flag that
    the GUI can check to know the engine was force-killed (so it can skip
    summarisation and post-processing).  Does NOT call os._exit — the GUI
    decides whether to exit the process.
    """
    global stop_event, engine_loop, _force_stopped
    _force_stopped = True
    if engine_loop and stop_event:
        engine_loop.call_soon_threadsafe(stop_event.set)


def was_force_stopped() -> bool:
    return _force_stopped


def get_session_snapshot() -> dict:
    """Return a dict capturing the current live sermon state for session restore."""
    return {
        "transcript":       full_sermon_transcript or "",
        "verses_cited":     list(verses_cited),
        "verse_history":    list(_verse_history),
        "current_book":     current_book,
        "current_chapter":  current_chapter,
        "current_verse":    current_verse,
        "sermon_anchor": {
            "book":    _sermon_anchor_book,
            "chapter": _sermon_anchor_chapter,
            "verse":   _sermon_anchor_verse,
        },
    }


def restore_session_snapshot(data: dict) -> None:
    """Restore engine state from a saved session snapshot dict."""
    global full_sermon_transcript, verses_cited, _verse_history
    global current_book, current_chapter, current_verse
    global _sermon_anchor_book, _sermon_anchor_chapter, _sermon_anchor_verse

    full_sermon_transcript = data.get("transcript", "")
    verses_cited           = list(data.get("verses_cited", []))
    _verse_history         = list(data.get("verse_history", []))

    anchor = data.get("sermon_anchor", {})
    _sermon_anchor_book    = anchor.get("book")
    _sermon_anchor_chapter = anchor.get("chapter")
    _sermon_anchor_verse   = anchor.get("verse")

    current_book    = data.get("current_book")    or _sermon_anchor_book
    current_chapter = data.get("current_chapter") or _sermon_anchor_chapter
    current_verse   = data.get("current_verse")   or _sermon_anchor_verse

    # Session restore injects context from outside the live audio stream.
    # Open a quarantine so the restored context is metadata only — the
    # operator must speak a reference before the engine will present anything.
    _open_system_quarantine("restore_session_snapshot")

    logger.info(
        f"📂 Session restored — anchor: {_sermon_anchor_book} {_sermon_anchor_chapter}:"
        f"{_sermon_anchor_verse}, {len(_verse_history)} verse(s) in history"
    )

def add_to_verse_history(ref: str, source: str = "MANUAL") -> None:
    """Add a verse to history without going through deliver_verse / Selenium.
    Used when the GUI sends a verse manually (text box or chapter browser click)
    so those refs still appear in the history panel and session notes.

    Issue A fix: reject refs that contain "None" or have no colon when they
    look like they should be verse refs, so history is never polluted with
    entries like "1 Chronicles 4None".

    Quarantine rule: system-side injections (MANUAL-ENTRY, CHAPTER-BROWSER,
    or any source that is not a live detection layer) open a quarantine window
    so the injected reference is metadata only and cannot silently steer the
    parser into presenting a verse.
    """
    import datetime as _dt2
    _ref = (ref or "").strip()

    # Guard: refuse any ref that contains the literal string "None"
    if "None" in _ref:
        logger.warning(
            f"⛔ add_to_verse_history rejected malformed ref '{_ref}' "
            f"(contains 'None') — history unchanged"
        )
        return

    # Guard: a non-empty ref must have recognisable structure
    # (at least "Book N" or "Book N:V")
    _parts = _ref.split()
    if len(_parts) < 2:
        logger.warning(
            f"⛔ add_to_verse_history rejected ref '{_ref}' — too short to be valid"
        )
        return

    _verse_history.append({
        "ref":   _ref,
        "time":  _dt2.datetime.now().strftime("%H:%M:%S"),
        "layer": source,
    })
    if _ref not in verses_cited:
        verses_cited.append(_ref)
    send_to_discord(_ref)
    logger.info(f"📋 Added to history ({source}): {_ref}")

    # System-side events are metadata only — open a quarantine so this
    # injection cannot steer subsequent inferred detections.
    _SYSTEM_SOURCES = {"MANUAL-ENTRY", "CHAPTER-BROWSER", "MANUAL", "RESTORE"}
    if source in _SYSTEM_SOURCES:
        _open_system_quarantine(f"add_to_verse_history({source})")

def clear_verse_history():
    _verse_history.clear()


# ── ONWARDS MODE ──────────────────────────────────────────────────────────────
onwards_active     = False
onwards_book       = None
onwards_chapter    = None
onwards_verse      = None
onwards_timer      = None
onwards_target_ref = None
onwards_trigger    = None
onwards_target_text = None


# Counter for consecutive NO matches — abort ONWARDS if clearly in wrong chapter
_onwards_consecutive_no = 0
# Bug EN-2 fix: raised from 5 → 12. Pastors who paraphrase/explain rather than
# reading verbatim would hit 5 NOs quickly even while still in the same chapter.
# 12 consecutive semantic mismatches gives more headroom before aborting.
_ONWARDS_MISMATCH_LIMIT = 12  # abort after this many straight NO results


def _stop_onwards():
    global onwards_active, onwards_timer, onwards_target_ref, onwards_trigger, _onwards_consecutive_no
    onwards_active          = False
    _onwards_consecutive_no = 0
    if onwards_timer:
        onwards_timer.cancel()
    onwards_timer      = None
    onwards_target_ref = None
    onwards_trigger    = None
    logger.info("⏹️ ONWARDS mode stopped")

def _cancel_vtc():
    global _vtc_pending_ref, _vtc_trigger_words, _vtc_timer, _vtc_source
    _vtc_source = "UNKNOWN"
    if _vtc_timer:
        _vtc_timer.cancel()
    _vtc_pending_ref   = None
    _vtc_trigger_words = []
    _vtc_timer         = None

def _start_vtc(ref, controller, source="UNKNOWN"):
    """Fetch verse text via Bible API, then use LLM semantic check to confirm it was spoken. New ref cancels previous."""
    global _vtc_pending_ref, _vtc_trigger_words, _vtc_timer, _vtc_source
    
    # Chapter-only refs (e.g. "John 3") have no specific verse text to match — skip VTC
    if ':' not in ref:
        logger.debug(f"🔀 VTC skip: {ref} is chapter-only (no verse text to match)")
        controller.send_verse(ref, bypass_cooldown=True, source=source)
        return

    if _vtc_pending_ref == ref:
        return # Ignore duplicate detections of the same verse we are already waiting for
        
    _cancel_vtc()  # void any previous pending ref (cancel-on-new-ref)
    _vtc_source = source

    text = fetch_verse_text(ref)
    if not text:
        # Retry once after 1s for transient API failures
        logger.debug(f"🔄 VTC: fetch_verse_text({ref}) returned None, retrying in 1s...")
        time.sleep(1.0)
        text = fetch_verse_text(ref)
    if not text:
        logger.warning(f"⚠️ VTC: Could not fetch text for {ref} after retry. Sending instantly.")
        controller.send_verse(ref, bypass_cooldown=True, source=source)
        return

    _vtc_pending_ref   = ref
    _vtc_trigger_words = [text]  # store full verse text in trigger_words[0] for LLM check
    logger.info(f"🎯 VTC: Waiting to hear {ref} (semantic match)")

    # 60s expiry
    _vtc_timer = threading.Timer(60.0, lambda: _vtc_expire(ref))
    _vtc_timer.daemon = True
    _vtc_timer.start()

def _vtc_expire(ref):
    global _vtc_pending_ref
    if _vtc_pending_ref == ref:
        logger.info(f"⏰ VTC expired: {ref} was never spoken — cleared")
        _cancel_vtc()

_vtc_semantic_in_flight = False
_vtc_last_check_time    = 0.0
_vtc_last_excerpt       = ""

def check_vtc(text, controller) -> bool:
    """Call this on every transcript blob. Returns True if VTC matched and sent."""
    global _vtc_pending_ref, _vtc_semantic_in_flight, _vtc_last_excerpt, _vtc_last_check_time
    if not _vtc_pending_ref or not _vtc_trigger_words:
        return False
        
    now = time.time()
    if now - _vtc_last_check_time < 3.0:
        return False # Minimum 3s between semantic checks for VTC
        
    verse_text = _vtc_trigger_words[0]
    excerpt    = _excerpt_since_last_advance(40)
    
    if (groq_client or cerebras_client) and excerpt:
        if _vtc_semantic_in_flight:
            return False
        if excerpt == _vtc_last_excerpt:
            return False
            
        current_ref = _vtc_pending_ref
        _vtc_semantic_in_flight = True
        _vtc_last_excerpt = excerpt
        _vtc_last_check_time = now
        
        def task():
            global _vtc_semantic_in_flight, _vtc_last_excerpt
            try:
                if _shutdown_flag.is_set():
                    return
                if _llm_semantic_match(verse_text, excerpt, label=current_ref):
                    if _shutdown_flag.is_set():
                        return
                    if _vtc_pending_ref == current_ref:
                        logger.info(f"✅ VTC confirmed: {current_ref}")
                        _cancel_vtc()
                        _mark_advance_offset()
                        controller.send_verse(current_ref, bypass_cooldown=True)
            except Exception:
                if _shutdown_flag.is_set():
                    return
                raise
            finally:
                _vtc_semantic_in_flight = False
                _vtc_last_excerpt = ""  # clear so the next new excerpt triggers a fresh check
                
        _vtc_t = threading.Thread(target=task, daemon=True)
        _active_bg_threads.append(_vtc_t)
        _vtc_t.start()
        return False
    return False


def _reset_onwards_timer():
    global onwards_timer
    if onwards_timer:
        onwards_timer.cancel()
    onwards_timer        = threading.Timer(60.0, _stop_onwards)
    onwards_timer.daemon = True
    onwards_timer.start()


def _fetch_next_onwards():
    global onwards_target_ref, onwards_trigger, onwards_target_text
    if not onwards_active:
        return
    next_v = onwards_verse + 1
    ref    = f"{onwards_book} {onwards_chapter}:{next_v}"
    text   = fetch_verse_text(ref)
    if text:
        onwards_target_text = text
        words           = re.findall(r'[a-z]+', text.lower())[:6]
        onwards_trigger    = " ".join(words)
        onwards_target_ref = ref
        logger.info(f"⏭️ ONWARDS READY: {ref}")
    else:
        logger.warning(f"⚠️ ONWARDS couldn't fetch {ref} — stopping.")
        _stop_onwards()


def _start_onwards(book, chapter, verse):
    global onwards_active, onwards_book, onwards_chapter, onwards_verse
    _stop_onwards()
    onwards_active  = True
    onwards_book    = book
    onwards_chapter = chapter
    onwards_verse   = int(verse)
    _reset_onwards_timer()
    logger.info(f"▶️ ONWARDS mode started from {book} {chapter}:{verse}")
    threading.Thread(target=_fetch_next_onwards, daemon=True).start()


_onwards_semantic_in_flight = False
_onwards_last_check_time    = 0.0
_onwards_last_excerpt       = ""

def _check_onwards_advance(text, controller) -> bool:
    global onwards_verse, _onwards_semantic_in_flight, _onwards_last_excerpt, _onwards_last_check_time
    if not onwards_active or not onwards_target_ref or not onwards_target_text:
        return False
        
    now = time.time()
    if now - _onwards_last_check_time < 3.0:
        return False # Minimum 3s between semantic checks for ONWARDS
        
    excerpt = _excerpt_since_last_advance(40)
    
    if excerpt and cerebras_client:
        if _onwards_semantic_in_flight:
            return False
        if excerpt == _onwards_last_excerpt:
            return False
            
        current_ref = onwards_target_ref
        current_text = onwards_target_text
        _onwards_semantic_in_flight = True
        _onwards_last_excerpt = excerpt
        _onwards_last_check_time = now
        
        def task():
            global onwards_verse, _onwards_semantic_in_flight, _onwards_last_excerpt, _onwards_consecutive_no
            try:
                if _shutdown_flag.is_set():
                    return
                matched = _llm_semantic_match(current_text, excerpt, label=f"ONWARDS {current_ref}")
                if _shutdown_flag.is_set():
                    return
                if matched:
                    if onwards_target_ref == current_ref:
                        _onwards_consecutive_no = 0  # reset mismatch counter on success
                        logger.info(f"🎯 ONWARDS ADVANCE: {current_ref} (Cerebras)")
                        _mark_advance_offset()
                        controller.send_verse(current_ref, bypass_cooldown=True, source="ONWARDS")
                        onwards_verse += 1
                        _reset_onwards_timer()
                        threading.Thread(target=_fetch_next_onwards, daemon=True).start()
                else:
                    # Bug 1: Track consecutive NO results to detect chapter mismatch
                    _onwards_consecutive_no += 1
                    if _onwards_consecutive_no >= _ONWARDS_MISMATCH_LIMIT:
                        logger.warning(
                            f"⚠️ ONWARDS MISMATCH: {_onwards_consecutive_no} consecutive NO results "
                            f"for {current_ref} — aborting ONWARDS (likely wrong chapter context)"
                        )
                        _stop_onwards()
            except Exception:
                if _shutdown_flag.is_set():
                    return
                raise
            finally:
                _onwards_semantic_in_flight = False
                _onwards_last_excerpt = ""  # clear so next new excerpt triggers a fresh check
                
        _onwards_t = threading.Thread(target=task, daemon=True)
        _active_bg_threads.append(_onwards_t)
        _onwards_t.start()
        return False

    # Fallback: legacy keyword trigger when no Cerebras client
    if not cerebras_client and onwards_trigger:
        transcript_words = set(re.findall(r'[a-z]+', text.lower()))
        check_words      = onwards_trigger.split()[:4]
        if not check_words:
            return False
        matches   = sum(1 for w in check_words if w in transcript_words)
        threshold = min(2, len(check_words))
        if matches >= threshold:
            logger.info(f"🎯 ONWARDS ADVANCE: {onwards_target_ref} (heard '{onwards_trigger[:30]}')")
            controller.send_verse(onwards_target_ref, bypass_cooldown=True, source="ONWARDS")
            onwards_verse += 1
            _reset_onwards_timer()
            threading.Thread(target=_fetch_next_onwards, daemon=True).start()
            return True
    return False


def queue_verse_range(book, chapter, start_verse, end_verse, controller):
    with verse_queue_lock:
        verse_queue.clear()

    def fetch_all():
        for v in range(start_verse + 1, end_verse + 1):
            ref  = f"{book} {chapter}:{v}"
            text = fetch_verse_text(ref)
            if text:
                with verse_queue_lock:
                    verse_queue.append((ref, text, time.time()))  # Add timestamp
                logger.info(f"📚 Queued: {ref}")

    threading.Thread(target=fetch_all, daemon=True).start()
    logger.info(f"📖 Range queued: {book} {chapter}:{start_verse} → {end_verse}")


_queue_semantic_in_flight = False
_queue_last_check_time    = 0.0
_queue_last_excerpt       = ""

def check_verse_queue(transcript, controller) -> bool:
    # NOTE: WORSHIP_MODE does NOT bail here — detection runs for debug logging.
    global _queue_semantic_in_flight, _queue_last_excerpt, _queue_last_check_time
    global current_book, current_chapter, current_verse
    with verse_queue_lock:
        if not verse_queue:
            return False
        next_ref, verse_text, queue_time = verse_queue[0]
        
    now = time.time()
    
    # Abandonment condition (a): Time-based — abandon after 3 minutes
    if now - queue_time > 180:  # 3 minutes = 180 seconds
        with verse_queue_lock:
            if verse_queue and verse_queue[0][0] == next_ref:
                verse_queue.pop(0)
                logger.info(f"⏰ QUEUE abandoned: {next_ref} — exceeded 3 min wait")
        return False
    
    # Abandonment conditions (b) and (c): verse-distance and book-change
    if current_book and current_chapter:
        try:
            queued_parts = next_ref.split()
            if len(queued_parts) >= 2 and ":" in queued_parts[-1]:
                queued_book = " ".join(queued_parts[:-1])
                queued_chapter, queued_verse_num = queued_parts[-1].split(":")
                
                # Condition (c): Different book — abandon immediately
                if queued_book.lower() != current_book.lower():
                    with verse_queue_lock:
                        if verse_queue and verse_queue[0][0] == next_ref:
                            verse_queue.pop(0)
                            logger.info(f"⏰ QUEUE abandoned: {next_ref} — sermon moved to different book")
                    return False
                
                # Condition (b): Same book, same chapter — check verse distance (5 verses ahead)
                if queued_chapter == current_chapter and current_verse:
                    if int(current_verse) >= int(queued_verse_num) + 5:
                        with verse_queue_lock:
                            if verse_queue and verse_queue[0][0] == next_ref:
                                verse_queue.pop(0)
                                logger.info(f"⏰ QUEUE abandoned: {next_ref} — sermon advanced past target")
                        return False
                
                # Condition (b-ext): Moved more than 1 chapter ahead in same book
                try:
                    if int(current_chapter) > int(queued_chapter) + 1:
                        with verse_queue_lock:
                            if verse_queue and verse_queue[0][0] == next_ref:
                                verse_queue.pop(0)
                                logger.info(f"⏰ QUEUE abandoned: {next_ref} — sermon advanced past target chapter")
                        return False
                except ValueError:
                    pass
        except (ValueError, IndexError):
            pass  # If parsing fails, continue with normal logic
    
    if now - _queue_last_check_time < 3.0:
        return False # Minimum 3s between semantic checks for QUEUE
        
    excerpt = _excerpt_since_last_advance(40)
    if not excerpt:
        return False
        
    if groq_client or cerebras_client:
        if _queue_semantic_in_flight:
            return False
        if excerpt == _queue_last_excerpt:
            return False
            
        current_ref = next_ref
        _queue_semantic_in_flight = True
        _queue_last_excerpt = excerpt
        _queue_last_check_time = now
        
        def task():
            global _queue_semantic_in_flight, _queue_last_excerpt
            try:
                if _shutdown_flag.is_set():
                    return
                if _llm_semantic_match(verse_text, excerpt, label=f"QUEUE {current_ref}"):
                    if _shutdown_flag.is_set():
                        return
                    with verse_queue_lock:
                        if verse_queue and verse_queue[0][0] == current_ref:
                            verse_queue.pop(0)
                        else:
                            return  # Queue advanced while we were checking
                    logger.info(f"🎯 AUTO-ADVANCE: {current_ref}")
                    _mark_advance_offset()
                    controller.send_verse(current_ref, bypass_cooldown=True, source="QUEUE")
            except Exception:
                if _shutdown_flag.is_set():
                    return
                raise
            finally:
                _queue_semantic_in_flight = False
                _queue_last_excerpt = ""  # clear so next new excerpt triggers a fresh check
                
        _queue_t = threading.Thread(target=task, daemon=True)
        _active_bg_threads.append(_queue_t)
        _queue_t.start()
        return False
    # Fallback: no LLM client → no auto-advance for this verse
    return False


def check_and_queue_range(text, base_ref, controller):
    if ":" not in base_ref:
        return
    num_norm = normalize_numbers_only(text)
    range_m  = RANGE_RE.search(num_norm)
    if not range_m:
        return
    try:
        end_v                     = int(range_m.group("end"))
        parts                     = base_ref.split()
        book                      = " ".join(parts[:-1])
        chap_str, startv_str      = parts[-1].split(":")
        start_v                   = int(startv_str)
        if end_v > start_v and end_v <= start_v + 30:
            queue_verse_range(book, chap_str, start_v, end_v, controller)
    except Exception:
        return


# ── DISCORD VERSE NOTIFICATION ────────────────────────────────────────────────
def send_to_discord(verse: str):
    # Bug 4 fix: Dual-STT streams can both call send_to_discord for the same ref
    # within milliseconds of each other.  Guard with a short dedup window so only
    # the first caller actually posts to the webhook; the second is silently dropped.
    global _discord_sent
    now_ds = time.time()
    last_ds = _discord_sent.get(verse, 0.0)
    if (now_ds - last_ds) < _DISCORD_DEDUP_SECS:
        logger.debug(f"📩 Discord send suppressed (duplicate within {_DISCORD_DEDUP_SECS}s): {verse}")
        return
    _discord_sent[verse] = now_ds

    def do_send(payload):
        try:
            r = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5, verify=certifi.where())
            if r.status_code == 204:
                logger.info("📩 Sent to Discord")
        except Exception as e:
            logger.error(f"Discord failed: {e}")

    lower = verse.lower().replace(" ", "")
    if "67" in lower or "6:7" in lower or re.search(r'6\s*7', lower):
        threading.Thread(target=do_send, args=({"content": "SIXX SEVENNN 🔥"},), daemon=True).start()

    threading.Thread(target=do_send, args=({"content": f"✝️ Verse Detected: {verse}"},), daemon=True).start()


def translate_to_english(text: str) -> str:
    if not text.strip():
        return text

    def _is_bad_translation(original: str, result: str) -> bool:
        """Return True if result looks like a failed/offensive/nonsensical translation."""
        if not result or not result.strip():
            return True
        r = result.strip()
        # Suspiciously short when input was long
        if len(original) > 30 and len(r) < 3:
            return True
        # Still contains substantial Malayalam Unicode (translation didn't work)
        ml_chars = sum(1 for c in r if '\u0D00' <= c <= '\u0D7F')
        if ml_chars > len(r) * 0.3:
            return True
        # Looks like an API error message
        if any(phrase in r.lower() for phrase in [
            "i cannot", "i can't", "translation failed", "error",
            "sorry", "unable to", "not able to",
        ]):
            return True
        return False

    try:
        url = "https://api.sarvam.ai/translate"
        headers = {
            "Content-Type": "application/json",
            "api-subscription-key": SARVAM_API_KEY
        }
        payload = {
            "input": text,
            "source_language_code": "ml-IN",
            "target_language_code": "en-IN",
            "model": "mayura:v1",
            "speaker_gender": "Male",
            "mode": "formal",
            "enable_preprocessing": True
        }
        r = requests.post(url, headers=headers, json=payload, timeout=5, verify=certifi.where())
        if r.status_code == 200:
            translated = r.json().get("translated_text", "")
            if translated and not _is_bad_translation(text, translated):
                return translated
    except Exception as e:
        logger.debug(f"Sarvam translate exception: {e}")

    try:
        if groq_client:
            prompt = f"Translate this Malayalam text to English. Return only the translated text, nothing else:\n{text}"
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={"model": "llama-3.1-8b-instant", "messages": [{"role": "user", "content": prompt}], "temperature": 0.2},
                timeout=5, verify=certifi.where()
            )
            if r.status_code == 200:
                translated = r.json()["choices"][0]["message"]["content"].strip()
                if translated and not translated.lower().startswith("translate this") and not _is_bad_translation(text, translated):
                    return translated
    except Exception as e:
        logger.debug(f"Groq translate exception: {e}")

    return text


# ── LLM VERSE EXTRACTION  (Groq only — llama-3.1-8b-instant) ─────────────────
def extract_verse_with_llm(text):
    global LLM_CALL_COUNT

    if not groq_client:
        return None

    # ── Anchor-match suppression ────────────────────────────────────────────
    # If the active sermon anchor is already set to this book+chapter, and the
    # text contains no explicit reference signal (no colon, no "chapter N verse N"),
    # skip LLM extraction entirely. The preacher is expounding a known passage,
    # not announcing a new one.  This prevents paraphrase-content false positives
    # where the LLM reverse-engineers a reference from verse text the preacher is
    # already explaining.
    _has_explicit_ref_signal = bool(
        re.search(r'[A-Za-z]\w*\s+\d{1,3}:\d{1,3}', text)  # colon notation
        or re.search(r'(?:chapter|chap|ch)\s+\d{1,3}\s+(?:verse|v)\s+\d{1,3}', text, re.IGNORECASE)  # spoken form
    )
    if current_book and current_chapter and not _has_explicit_ref_signal:
        # No explicit reference signal — the text is likely exposition/paraphrase
        logger.debug(
            f"🤖 LLM extraction SKIPPED (anchor-match suppression): "
            f"active anchor {current_book} {current_chapter} — no explicit ref signal in text"
        )
        return None

    context_hint = ""
    if current_book and current_chapter:
        # Bug ML-1 fix: include how far through the chapter the sermon has progressed.
        # Without this, the LLM has no memory of verse position and can jump back to
        # verse 1 (or any early verse) even when the sermon is near verse 17+.
        _hw_key   = f"{current_book} {current_chapter}"
        _hw_verse = _session_verse_high_water.get(_hw_key, 0)
        context_hint = (
            f"\nContext: The speaker is currently reading from "
            f"{current_book} chapter {current_chapter}."
        )
        if _hw_verse > 0:
            _floor = max(1, _hw_verse - 2)
            context_hint += (
                f" The sermon has already covered up to at least verse {_hw_verse} of this chapter. "
                f"Do NOT suggest any verse earlier than verse {_floor} unless the transcript "
                f"explicitly states the speaker is going back (e.g. 'let's return to verse 1', "
                f"'going back to the beginning'). Strongly prefer verses {_hw_verse} or later."
            )

    try:
        LLM_CALL_COUNT += 1
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{
                "role": "user",
                "content": (
                    f"You are a Bible reference detector for a live sermon. "
                    f"Your ONLY job is to detect when the SPEAKER EXPLICITLY NAMES or READS "
                    f"a Bible reference — NOT when the text merely resembles or paraphrases "
                    f"verse content.\n\n"
                    f"STRICT RULES:\n"
                    f"1. Return a reference ONLY if the speaker explicitly says a book name "
                    f"   followed by chapter and verse (e.g. 'Acts chapter 1 verse 8', 'Acts 1:8').\n"
                    f"2. If the text is a PARAPHRASE, EXPOSITION, or SERMON ILLUSTRATION "
                    f"   that happens to match verse content (e.g. 'you will be my witnesses' "
                    f"   or 'to the ends of the earth'), return NONE — this is NOT a citation.\n"
                    f"3. Return ONLY in format 'Book Chapter:Verse' (e.g., John 3:16).\n"
                    f"4. If no explicit reference is found, return exactly NONE.{context_hint}\n\n"
                    f"Text: {text}"
                ),
            }],
        )
        verse = response.choices[0].message.content.strip()
        if verse == "NONE":
            return None
        if re.match(r'^[1-3]?[A-Za-z ]{1,30}\d{1,3}:\d{1,3}$', verse):
            logger.info(f"🤖 LLM extracted: {verse}")
            return verse
        return None
    except Exception as e:
        logger.error(f"❌ LLM error: {e}")
        return None


# Tracks where full_sermon_transcript ended when the last verse was auto-advanced.
# The semantic check only sees words spoken AFTER this point, so old verse text
# that is still in the rolling window cannot immediately trigger the next verse.
_advance_transcript_offset: int = 0


def _mark_advance_offset():
    """Call this every time an auto-advance fires. Pins the current transcript length
    so the next Cerebras check only sees NEW words spoken after this moment."""
    global _advance_transcript_offset
    _advance_transcript_offset = len(full_sermon_transcript)


def _recent_transcript_excerpt(max_words: int = 30) -> str:
    """Return the last N words of the running transcript (full window — used by Layer 9 LLM)."""
    words = full_sermon_transcript.strip().split()
    if not words:
        return ""
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[-max_words:])


def _excerpt_since_last_advance(max_words: int = 40) -> str:
    """Return only the words spoken SINCE the last auto-advance.
    This prevents the previous verse's text from immediately triggering the next verse."""
    tail = full_sermon_transcript[_advance_transcript_offset:].strip()
    if not tail:
        return ""
    words = tail.split()
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[-max_words:])


def _llm_semantic_match(verse_text: str, transcript_excerpt: str, label: str = "") -> bool:
    """Use Groq llama-3.1-8b-instant (fallback: Cerebras) to check if transcript matches a verse.
    Bug 1: Groq has a separate quota from the outline generator (Cerebras), so routing semantic
    match here protects the Cerebras quota for the live outline loop."""
    # Bug 1: prefer Groq to keep Cerebras quota exclusively for the outline generator
    _client     = groq_client or cerebras_client
    _model      = "llama-3.1-8b-instant" if _client is groq_client else "llama3.1-8b"
    _client_tag = "Groq" if _client is groq_client else "Cerebras"
    if not _client:
        return False
    verse_text = (verse_text or "").strip()
    transcript_excerpt = (transcript_excerpt or "").strip()
    if not verse_text or not transcript_excerpt:
        return False
    logger.info(f"🧠 {_client_tag}{(' [' + label + ']') if label else ''}: checking '{transcript_excerpt[-60:]}' vs verse")
    prompt = (
        "You are helping a live Bible reading auto-advance system.\n"
        "A specific Bible verse is shown below. Below that are the ONLY words spoken aloud "
        "since this verse was last displayed on screen — no earlier transcript is included.\n\n"
        f"Bible verse to detect:\n{verse_text}\n\n"
        f"Words spoken since the last verse was shown:\n{transcript_excerpt}\n\n"
        "Question: Has the speaker substantially read or quoted this verse in the words above? "
        "Only say YES if the key content of this verse is clearly present in what was just spoken "
        "(paraphrasing or a different translation is fine, but the verse idea must actually appear "
        "— do NOT say YES just because a single common word like 'love' or 'God' is there).\n"
        "Answer with YES or NO only."
    )
    try:
        response = _client.chat.completions.create(
            model=_model,
            messages=[{"role": "user", "content": prompt}],
        )
        answer = response.choices[0].message.content.strip().upper()
        result = answer.startswith("YES")
        logger.info(f"🧠 {_client_tag}{(' [' + label + ']') if label else ''}: → {'YES ✅' if result else 'NO ❌'}")
        return result
    except Exception as e:
        logger.error(f"❌ Semantic match error ({_client_tag}): {e}")
        return False


# ── VERSE CONTROLLER ──────────────────────────────────────────────────────────
class VerseController:
    def __init__(self):
        self.driver        = None
        self.box           = None
        self.btn           = None
        self.last_sent     = None
        self.last_time     = 0
        self.history       = {}
        self.pending_verse = None
        self.match_count   = 0
        self._send_lock    = threading.Lock()  # protects send_verse against timer-thread races

    def connect(self):
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from webdriver_manager.chrome import ChromeDriverManager

            logger.info(f"Connecting to VerseView at {REMOTE_URL}...")
            options = webdriver.ChromeOptions()
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-sync")
            options.add_argument("--disable-background-networking")
            options.add_argument("--disable-default-apps")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-translate")
            options.add_argument("--metrics-recording-only")
            options.add_argument("--mute-audio")
            options.add_argument("--log-level=3")
            options.add_experimental_option("excludeSwitches", ["enable-logging"])
            options.add_argument("--window-size=800,600")

            # Bug 3: check the wdm cache directory directly before calling ChromeDriverManager.
            # ChromeDriverManager().install() always fires 2 remote HTTP calls to resolve the
            # matching driver version even if the binary is already cached.  By globbing the
            # cache ourselves we skip those network round-trips entirely when a driver exists.
            import glob as _glob
            _wdm_root    = os.path.join(os.path.expanduser("~"), ".wdm", "drivers", "chromedriver")
            _exe_name    = "chromedriver.exe" if IS_WINDOWS else "chromedriver"
            _cached_hits = _glob.glob(os.path.join(_wdm_root, "**", _exe_name), recursive=True)
            if _cached_hits:
                _driver_path = max(_cached_hits, key=os.path.getmtime)
                logger.info(f"ChromeDriver loaded from cache (no CDN check): {_driver_path}")
            else:
                _driver_path = ChromeDriverManager().install()
                logger.info(f"ChromeDriver freshly downloaded: {_driver_path}")
            self.driver = webdriver.Chrome(
                service=Service(_driver_path),
                options=options,
            )
            self.driver.get(REMOTE_URL)
            wait     = WebDriverWait(self.driver, 15)
            self.box = wait.until(EC.presence_of_element_located((By.ID, "remote_bibleRefID")))

            btn = None
            selectors = [
                (By.ID,    "remote_bible_present"),
                (By.XPATH, "//button[contains(normalize-space(text()),'PRESENT')]"),
                (By.XPATH, "//button[contains(normalize-space(text()),'Present')]"),
                (By.XPATH, "//button[contains(@onclick,'present')]"),
                (By.XPATH, "//input[@type='button'][contains(@value,'PRESENT')]"),
            ]
            for by, selector in selectors:
                try:
                    btn = self.driver.find_element(by, selector)
                    logger.info(f"Found PRESENT button: {selector}")
                    break
                except Exception:
                    continue

            if not btn:
                all_btns = self.driver.find_elements(By.TAG_NAME, "button")
                logger.error("Could not find PRESENT button.")
                for b in all_btns:
                    logger.error(f"  id={b.get_attribute('id')} text={b.text}")
                return False

            self.btn = btn
            logger.info("Connected to VerseView (headless mode)")
            return True
        except Exception as e:
            logger.error(f"VerseView connection failed: {e}")
            if self.driver:
                try: self.driver.quit()  # type: ignore
                except Exception: pass
                self.driver = None
            return False

    def close_presentation(self):
        if not self.driver:
            return
        try:
            from selenium.webdriver.common.by import By
            close_btn = self.driver.find_element(By.ID, "iconClose")
            close_btn.click()
            logger.info("🚫 Presentation cleared off the screen!")
        except Exception as e:
            logger.debug(f"Could not click close button (maybe already closed): {e}")

    def send_verse(self, ref, bypass_cooldown=False, confidence=1.0, source="UNKNOWN"):
        with self._send_lock:
            global current_book, current_chapter, current_verse, verses_cited
            global _session_verse_high_water
            # Worship Mode is the master gate — detection ran and logged above, but
            # nothing gets sent to the display (Selenium / VerseView) while worship is active.
            if WORSHIP_MODE:
                logger.info(f"🎵 [WORSHIP MODE] Detected but suppressed: {ref}")
                return False
            now = time.time()
            logger.debug(f"VerseController.send_verse: ref={ref}, bypass={bypass_cooldown}")

            # ── CHAPTER-ONLY REF: update context + chapter browser, do NOT present ──
            # When the speaker says "Matthew chapter 5" with no verse, we set context
            # so the chapter browser auto-reloads and the parser has the right book/chapter.
            # We do NOT send to Selenium — VerseView would default to verse 1 which is wrong.
            if ":" not in ref:
                _parts = ref.split()
                if len(_parts) >= 2:
                    _hw = _session_verse_high_water.get(ref)
                    if _hw:
                        # We've already been tracking verses in this chapter this session —
                        # upgrade to the last known verse so display resumes correctly.
                        # Validate first — if the upgraded ref is out of range, skip display
                        # rather than sending a bad ref that will cause the browser to alert.
                        _upgraded = f"{ref}:{_hw}"
                        if _reject_verse_out_of_range(_upgraded):
                            logger.warning(
                                f"⚠️ Skipping chapter resume — hw verse {_hw} is out of range for {ref}"
                            )
                            new_book    = " ".join(_parts[:-1])
                            new_chapter = _parts[-1]
                            current_book    = new_book
                            current_chapter = new_chapter
                            current_verse   = None
                            return True
                        ref = _upgraded
                        logger.info(f"📍 Resuming: chapter ref → {ref} (last known verse this session)")
                    else:
                        # Pure chapter-only: just update context, skip display
                        new_book    = " ".join(_parts[:-1])
                        new_chapter = _parts[-1]
                        current_book    = new_book
                        current_chapter = new_chapter
                        current_verse   = None
                        logger.info(f"📌 Chapter context set (no display): {new_book} {new_chapter}")
                        return True

            # ── MANUAL CONFIRMATION ──
            if confidence < CONFIDENCE_THRESHOLD and not bypass_cooldown:
                if REQUIRE_MANUAL_CONFIRM and CONFIRM_CALLBACK:
                    def _ask_thread():
                        logger.info(
                            f"🤔 Holding for manual confirmation: {ref} "
                            f"(Confidence: {int(confidence*100)}%)"
                        )
                        if CONFIRM_CALLBACK(ref, confidence):
                            logger.info(f"✅ User manually approved: {ref}")
                            self.send_verse(ref, bypass_cooldown=True, confidence=1.0, source=source)
                        else:
                            logger.info(f"❌ User rejected: {ref}")
                    threading.Thread(target=_ask_thread, daemon=True).start()
                    return False
                else:
                    logger.warning(
                        f"⚠️ Blocked: {ref} (Confidence {int(confidence*100)}% "
                        f"< Threshold {int(CONFIDENCE_THRESHOLD*100)}%)"
                    )
                    return False

            # ── VERIFICATION (hear twice) ──
            if REQUIRE_VERIFY and not bypass_cooldown:
                if self.pending_verse == ref:
                    self.match_count += 1
                else:
                    self.pending_verse = ref
                    self.match_count   = 1
                    logger.info(f"⏳ Verification pending for: {ref} (Heard once...)")
                    return False
                if self.match_count < 2:
                    return False
                self.pending_verse = None
                self.match_count   = 0

            # Bug 2: dedup same book+chapter within 10 seconds (unless verse changed)
            global _last_presented_book_chapter, _last_presented_time
            parts = ref.split()
            if len(parts) >= 2:
                book_chapter_key = " ".join(parts[:-1])
                if ":" in parts[-1]:
                    book_chapter_key += " " + parts[-1].split(":")[0]
                else:
                    book_chapter_key += " " + parts[-1]
            
                if (_last_presented_book_chapter == book_chapter_key and 
                    (now - _last_presented_time) < 10):
                    # Update the time even when blocking to prevent infinite blocking
                    _last_presented_time = now
                    logger.debug(f"Skipped duplicate chapter within 10s: {ref}")
                    return False

            # Always update the time when presenting
            _last_presented_book_chapter = book_chapter_key
            _last_presented_time = now

            # ── COOLDOWNS ──
            # Bug 3: 20-second deduplication for exact verse matches (always applies)
            if ref in self.history:
                elapsed = now - self.history[ref]
                if elapsed < 20:
                    logger.info(f"🔁 Suppressed duplicate: {ref} (within 20s window, {elapsed:.1f}s elapsed)")
                    return False
            if ref in self.history and (now - self.history[ref]) < DEDUP_WINDOW:
                logger.debug(f"Skipped duplicate: {ref}")
                return False
            if not bypass_cooldown and self.last_sent and (now - self.last_time) < COOLDOWN:
                logger.debug(f"Cooldown active: {ref}")
                return False

            # ── SEND ──
            try:
                if not self.driver:
                    if not self.connect():
                        return False

                # Dismiss any stale alert left open by a previous bad send (e.g. a
                # chapter-only ref that the website rejected with an alert dialog).
                # If we don't clear it first, the next execute_script throws
                # "unexpected alert open" and the real verse never gets through.
                try:
                    from selenium.webdriver.support.ui import WebDriverWait
                    from selenium.webdriver.support import expected_conditions as EC
                    alert = self.driver.switch_to.alert
                    alert_text = alert.text
                    logger.warning(f"⚠️ Stale browser alert detected — dismissing before send: \"{alert_text}\"")
                    alert.dismiss()
                except Exception:
                    pass  # No alert present — proceed normally

                self.driver.execute_script("arguments[0].value = arguments[1];", self.box, ref)
                self.driver.execute_script("arguments[0].click();", self.btn)
                logger.info(f"✅ PRESENTED: {ref}")
                _trigger_atem_keyer()

                _verse_history.append({
                    "ref": ref,
                    "time": _dt.datetime.now().strftime("%H:%M:%S"),
                    "layer": source
                })

                if ref not in verses_cited:
                    verses_cited.append(ref)

                send_to_discord(ref)

                parts = ref.split()
                if len(parts) >= 2:
                    global _sermon_anchor_book, _sermon_anchor_chapter, _sermon_anchor_verse
                    global _xref_anchor_book, _xref_anchor_chapter, _xref_anchor_verse, _xref_anchor_time
                    old_book_chapter = f"{current_book} {current_chapter}" if current_book and current_chapter else None
                    new_book    = " ".join(parts[:-1])
                    if ":" in parts[-1]:
                        new_chapter, new_verse_str = parts[-1].split(":")
                    else:
                        new_chapter   = parts[-1]
                        new_verse_str = None

                    # ── Sermon-anchor vs cross-reference-anchor decision ──────────────
                    # A ref is treated as a cross-reference (not a sermon move) when:
                    #   • the sermon anchor is already established, AND
                    #   • the incoming ref is in a DIFFERENT book than the sermon anchor.
                    # In that case we park it as a temporary xref and do NOT overwrite
                    # current_book/chapter/verse so contextual "verse N" keeps resolving
                    # against the main sermon passage.
                    _is_xref = (
                        _sermon_anchor_book is not None
                        and new_book.lower() != _sermon_anchor_book.lower()
                    )
                    if _is_xref:
                        _xref_anchor_book    = new_book
                        _xref_anchor_chapter = new_chapter
                        _xref_anchor_verse   = new_verse_str
                        _xref_anchor_time    = time.time()
                        logger.info(
                            f"📎 XREF ANCHOR set: {new_book} {new_chapter}:{new_verse_str or '?'}  "
                            f"— sermon anchor stays: "
                            f"{_sermon_anchor_book} {_sermon_anchor_chapter}:{_sermon_anchor_verse or '?'}  "
                            f"— contextual 'verse N' will resolve against sermon anchor"
                        )
                        # current_book/chapter/verse intentionally NOT updated — stays on sermon
                    else:
                        # Sermon is moving (same book, or first explicit ref ever)
                        current_book    = new_book
                        current_chapter = new_chapter
                        current_verse   = new_verse_str
                        _sermon_anchor_book    = new_book
                        _sermon_anchor_chapter = new_chapter
                        _sermon_anchor_verse   = new_verse_str
                        # Clear stale xref anchor — sermon itself moved
                        _xref_anchor_book    = None
                        _xref_anchor_chapter = None
                        _xref_anchor_verse   = None
                        _xref_anchor_time    = 0.0
                        logger.info(
                            f"📌 SERMON ANCHOR updated: "
                            f"{_sermon_anchor_book} {_sermon_anchor_chapter}:{_sermon_anchor_verse or '?'}"
                        )

                # Bug 1: Reset range latch when passage changes
                    new_book_chapter = f"{current_book} {current_chapter}"
                    if old_book_chapter != new_book_chapter:
                        global _range_latch_active, _range_latch_ref
                        _range_latch_active = False
                        _range_latch_ref = None

                self.history[ref] = now
                self.last_sent    = ref
                self.last_time    = now
            
                # Bug 2: update book+chapter tracking
                parts = ref.split()
                if len(parts) >= 2:
                    book_chapter_key = " ".join(parts[:-1])
                    if ":" in parts[-1]:
                        book_chapter_key += " " + parts[-1].split(":")[0]
                    else:
                        book_chapter_key += " " + parts[-1]
                    _last_presented_book_chapter = book_chapter_key
                    _last_presented_time = now

                # Bug 4: Update high-water mark for the chapter whenever a verse-level ref is sent
                if ":" in ref:
                    _hwp = ref.split()
                    if len(_hwp) >= 2 and ":" in _hwp[-1]:
                        _chap_key   = " ".join(_hwp[:-1]) + " " + _hwp[-1].split(":")[0]
                        _verse_num  = int(_hwp[-1].split(":")[1])
                        if _verse_num > _session_verse_high_water.get(_chap_key, 0):
                            _session_verse_high_water[_chap_key] = _verse_num
                        # Bug ML-3 fix: always track last-presented verse position (not just
                        # the high-water). This lets contextual detection reject backward jumps
                        # even when the sermon re-reads a lower verse that was the chapter max.
                        global _last_presented_verse_num, _last_presented_verse_book_chap
                        _last_presented_verse_num       = _verse_num
                        _last_presented_verse_book_chap = _chap_key

                if len(self.history) > 20:
                    oldest = min(self.history.items(), key=lambda x: x[1])
                    del self.history[oldest[0]]

                return True
            except Exception as e:
                logger.error(f"Failed to send {ref}: {e}")
                try:
                    self.driver.quit()
                except Exception:
                    pass
                self.driver = None
                return False

    def cleanup(self):
        if self.driver:
            try:
                self.driver.quit()
                logger.info("VerseView connection closed")
            except Exception:
                pass


# ── HYBRID VERSE DETECTOR ─────────────────────────────────────────────────────
ONWARDS_KEYWORDS = ["onwards", "onward", "and following", "and beyond", "and after"]

# Phrases that indicate "we're now in book X" — set context so next "Chapter N" uses this book
BOOK_CONTEXT_PHRASES = re.compile(
    r"(?:turn\s+(?:to|in)\s+(?:the\s+)?book\s+of"
    r"|open\s+(?:your\s+)?(?:bibles?\s+)?to\s+(?:the\s+)?book\s+of"
    r"|let'?s?\s+turn\s+(?:to|in)\s+(?:the\s+)?book\s+of"
    r"|i\s+want\s+to\s+take\s+you\s+to\s+(?:the\s+)?book\s+of"
    r"|we'?re?\s+going\s+to\s+(?:the\s+)?book\s+of"
    r"|we'?re?\s+reading\s+from\s+(?:the\s+)?book\s+of"
    r"|we'?re?\s+in\s+(?:the\s+)?book\s+of"
    r"|here\s+in\s+(?:the\s+)?book\s+of"
    r"|reading\s+in\s+(?:the\s+)?book\s+of"
    r"|(?:let'?s?\s+)?read\s+from\s+(?:the\s+)?book\s+of"
    r"|in\s+(?:the\s+)?book\s+of"
    r"|from\s+(?:the\s+)?book\s+of"
    r"|take\s+your\s+bibles?\s+to\s+(?:the\s+)?book\s+of"
    r"|(?:bring(?:ing)?|have)\s+(?:our|your\s+)?attention\s+(?:in|to)\s+(?:the\s+)?book\s+of"
    r"|attention\s+(?:in|to)\s+(?:the\s+)?book\s+of)\s+"
    r"([0-9a-z]+(?:\s+[0-9a-z]+){0,2})",
    re.IGNORECASE,
)


def _apply_book_context_if_mentioned(text: str) -> bool:
    """If text mentions 'book of X' or 'attention in the book of X', set current book and clear chapter/verse. Returns True if context was set."""
    global current_book, current_chapter, current_verse
    global _last_book_context_book, _last_book_context_hash, _last_book_context_time

    # Bug 3: Use the LAST match so accumulated text always reflects the most recent book
    all_matches = list(BOOK_CONTEXT_PHRASES.finditer(text))
    if not all_matches:
        return False
    m = all_matches[-1]

    # Bug 4: Guard casual/narrative references that precede the match
    pre_text = text[:m.start()]
    if _BOOK_CONTEXT_CASUAL_RE.search(pre_text[-80:] if len(pre_text) > 80 else pre_text):
        logger.debug(f"📖 Book context skipped (casual ref): '{m.group(1).strip()}'")
        return False

    raw  = m.group(1).strip()
    book = resolve_book_eng(raw)
    if not book:
        return False
    
    # Additional validation: ensure there's a reference structure nearby
    # (chapter, verse, number, or reference keyword)
    # Check both before and after the match
    context_window = text[max(0, m.start()-20):m.end()+50]
    has_reference = bool(
        re.search(r'\b(?:chapter|chap|ch|verse|verses)\b', context_window, re.IGNORECASE) or
        re.search(r'\d+', context_window) or
        ':' in context_window
    )
    
    # Issue 6: For explicit reading instructions, allow context setting without reference structure
    explicit_phrases = [
        r'\bturn\s+(?:to|in)\s+(?:the\s+)?book\s+of\b',
        r'\bopen\s+(?:your\s+)?(?:bibles?\s+)?to\s+(?:the\s+)?book\s+of\b',
        r'\blet\'?s?\s+turn\s+(?:to|in)\s+(?:the\s+)?book\s+of\b',
        r'\bi\s+want\s+to\s+take\s+you\s+to\s+(?:the\s+)?book\s+of\b',
        r'\bwe\'?re?\s+going\s+to\s+(?:the\s+)?book\s+of\b',
        r'\bwe\'?re?\s+reading\s+from\s+(?:the\s+)?book\s+of\b',
        r'\b(?:let\'?s?\s+)?read\s+from\s+(?:the\s+)?book\s+of\b',
        r'\b(?:bring(?:ing)?|have)\s+(?:our|your\s+)?attention\s+(?:in|to)\s+(?:the\s+)?book\s+of\b',
        r'\battention\s+(?:in|to)\s+(?:the\s+)?book\s+of\b'
    ]
    is_explicit_instruction = any(re.search(p, text, re.IGNORECASE) for p in explicit_phrases)
    
    if not has_reference and not is_explicit_instruction:
        # BUG 6: Log casual mentions as MENTION (no context change) instead of debug
        logger.info(f"\U0001f4d6 MENTION (no context change): '{book}'")
        return False

    # Bug 4: Dedup — skip silently if same book from same phrase hash
    import hashlib as _hashlib
    phrase_hash = _hashlib.md5(raw.lower().encode()).hexdigest()[:8]
    if book == _last_book_context_book and phrase_hash == _last_book_context_hash:
        return False

    _last_book_context_book = book
    _last_book_context_hash = phrase_hash
    _last_book_context_time = time.time()

    current_book    = book
    current_chapter = None
    current_verse   = None
    logger.info(f"📖 Book context set to: {book} (from '…book of {raw}…')")
    return True


def _dedup_blocked(text: str, reason: str) -> bool:
    """Return True (and record) the first time this BLOCKED event fires; suppress repeats for 30s."""
    import hashlib as _hl
    key = _hl.md5((text[:120] + "|" + reason).encode()).hexdigest()[:12]
    now = time.time()
    expired = [k for k, t in _blocked_context_hashes.items() if now - t > _BLOCKED_DEDUP_SECS]
    for k in expired:
        del _blocked_context_hashes[k]
    if key in _blocked_context_hashes:
        return False
    _blocked_context_hashes[key] = now
    return True


def _reject_verse_out_of_range(ref: str) -> bool:
    """Return True if the verse number in ref exceeds the known maximum for that
    specific book+chapter, or _MAX_VERSE_NUMBER (200) as a universal backstop.
    Logs a rejection line so it is visible in the log without presenting.

    Bug 2 fix: The simple '>200' check was not enough — it let through phantom
    verses like Isaiah 53:29 (Isaiah 53 has only 12 verses).  A per-chapter table
    covering every Bible chapter is included so out-of-range verse numbers are
    caught before they hit the display.
    """
    if ":" not in ref:
        return False
    try:
        verse_num = int(ref.rsplit(":", 1)[-1].split()[0])
        if verse_num > _MAX_VERSE_NUMBER:
            logger.info(f"🚫 REJECTED: verse number out of range ({ref})")
            return True
    except (ValueError, IndexError):
        return False

    # Per-chapter verse count table (Bug 2 fix).
    # Format: book_name_lower → [verses_in_ch1, verses_in_ch2, …]
    # Only books that have been involved in false-positive incidents need to be
    # listed; unlisted books fall back to the '>200' guard above.
    _CHAPTER_VERSE_COUNTS: dict[str, list[int]] = {
        # OT
        "genesis":       [31,25,24,26,32,22,24,22,29,32,32,20,18,24,21,16,27,33,38,18,34,24,20,67,34,35,46,22,35,43,55,32,20,31,29,43,36,30,23,23,57,38,34,34,28,34,31,22,33,26],
        "exodus":        [22,25,22,31,23,30,25,32,35,29,10,51,22,31,27,36,16,27,25,26,36,31,33,18,40,37,21,43,46,38,18,35,23,35,35,38,29,31,43,38],
        "leviticus":     [17,16,17,35,19,30,38,36,24,20,47,8,59,57,33,34,16,30,24,46,22,22,15,22,15,22,21,25,22,25,22,18,22,26],
        "numbers":       [54,34,51,49,31,27,89,26,23,36,35,16,33,45,41,50,13,32,22,29,35,41,30,25,18,65,23,31,40,16,54,42,56,29,34,13],
        "deuteronomy":   [46,37,29,49,33,25,26,20,29,22,32,32,18,29,23,22,20,22,21,20,23,30,25,22,19,19,26,68,29,20,30,52,29,12],
        "joshua":        [18,24,17,24,15,27,26,35,27,43,23,24,33,15,63,10,18,28,51,9,45,34,16,33],
        "judges":        [36,23,31,24,31,40,25,35,57,18,40,15,25,20,20,31,13,31,30,48,25],
        "ruth":          [22,23,18,22],
        "1 samuel":      [28,36,21,22,12,21,17,22,27,27,15,25,23,52,35,23,58,30,24,42,15,23,29,22,44,25,12,25,11,31,13],
        "2 samuel":      [27,32,39,12,25,23,29,18,13,19,27,31,39,33,37,23,29,33,43,26,22,51,39,25],
        "1 kings":       [53,46,28,34,18,38,51,66,28,29,43,33,34,31,34,34,24,46,21,43,29,53],
        "2 kings":       [18,25,27,44,27,33,20,29,37,36,21,21,25,29,38,20,41,37,37,21,26,20,37,20,30],
        "1 chronicles":  [54,55,24,43,26,81,40,40,44,14,47,40,14,17,29,43,27,17,19,8,30,19,32,31,31,32,34,21,30],
        "2 chronicles":  [17,18,17,22,14,42,22,18,31,19,23,16,22,15,19,14,19,34,11,37,20,12,21,27,28,23,9,27,36,27,21,33,25,33,27,23],
        "ezra":          [11,70,13,24,17,22,28,36,15,44],
        "nehemiah":      [11,20,32,23,19,19,73,18,38,39,36,47,31],
        "esther":        [22,23,15,17,14,14,10,17,32,3],
        "job":           [22,13,26,21,27,30,21,22,35,22,20,25,28,22,35,22,16,21,29,29,34,30,17,25,6,14,23,28,25,31,40,22,33,37,16,33,24,41,30,24,34,17],
        "psalms":        [6,12,8,8,12,10,17,9,20,18,7,8,6,7,5,11,15,50,14,9,13,31,6,10,22,12,14,9,11,12,24,11,22,22,28,12,40,22,13,17,13,11,5,26,17,11,9,14,20,23,19,9,6,7,23,13,11,11,17,12,8,12,11,10,13,20,7,35,36,5,24,20,28,23,10,12,20,72,13,19,16,8,18,12,13,17,7,18,52,17,16,15,5,23,11,13,12,9,9,5,8,28,22,35,45,48,43,13,31,7,10,10,9,8,18,19,2,29,176,7,8,9,4,8,5,6,5,6,8,8,3,18,3,3,21,26,9,8,24,14,10,8,12,15,21,10,20,14,9,6],
        "proverbs":      [33,22,35,27,23,35,27,36,18,32,31,28,25,35,33,33,28,24,29,30,31,29,35,34,28,28,27,28,27,33,31],
        "ecclesiastes":  [18,26,22,16,20,12,29,17,18,20,10,14],
        "song of solomon":[17,17,11,16,16,13,13,14],
        "isaiah":        [31,22,26,6,30,13,25,22,21,34,16,6,22,32,9,14,14,7,25,6,17,25,18,23,12,21,13,29,24,33,9,20,24,17,10,22,38,22,8,31,29,25,28,28,25,13,15,22,26,11,23,15,12,17,13,12,21,14,21,22,11,12,19,12,25,24],
        "jeremiah":      [19,37,25,31,31,30,34,22,26,25,23,17,27,22,21,21,27,23,15,18,14,30,40,10,38,24,22,17,32,24,40,44,26,22,19,32,20,28,18,16,18,22,13,30,5,28,7,47,39,46,64,34],
        "lamentations":  [22,22,66,22,22],
        "ezekiel":       [28,10,27,17,17,14,27,18,11,22,25,28,23,23,8,63,24,32,14,49,32,31,49,27,17,21,36,26,21,26,18,32,33,31,15,38,28,23,29,49,26,20,27,31,25,24,23,35],
        "daniel":        [21,49,30,37,31,28,28,27,27,21,45,13],
        "hosea":         [11,23,5,19,15,11,16,14,17,15,12,14,16,9],
        "joel":          [20,32,21],
        "amos":          [15,16,15,13,27,14,17,14,15],
        "obadiah":       [21],
        "jonah":         [17,10,10,11],
        "micah":         [16,13,12,13,15,16,20],
        "nahum":         [15,13,19],
        "habakkuk":      [17,20,19],
        "zephaniah":     [18,15,20],
        "haggai":        [15,23],
        "zechariah":     [21,13,10,14,11,15,14,23,17,12,17,14,9,21],
        "malachi":       [14,17,18,6],
        # NT
        "matthew":       [25,23,17,25,48,34,29,34,38,42,30,50,58,36,39,28,27,35,30,34,46,46,39,51,46,75,66,20],
        "mark":          [45,28,35,41,43,56,37,38,50,52,33,44,37,72,47,20],
        "luke":          [80,52,38,44,39,49,50,56,62,42,54,59,35,35,32,31,37,43,48,47,38,71,56,53],
        "john":          [51,25,36,54,47,71,53,59,41,42,57,50,38,31,27,33,26,40,42,31,25],
        "acts":          [26,47,26,37,42,15,60,40,43,48,30,25,52,28,41,40,34,28,41,38,40,30,35,27,27,32,44,31],
        "romans":        [32,29,31,25,21,23,25,39,33,21,36,21,14,23,33,27],
        "1 corinthians": [31,16,23,21,13,20,40,34,16,30,20,11,12,11,15,23,64,11,15,10],
        "2 corinthians": [24,17,18,18,21,18,16,24,15,18,33,21,14],
        "galatians":     [24,21,29,31,26,18],
        "ephesians":     [23,22,21,28,20,32],
        "philippians":   [30,18,19,16],
        "colossians":    [29,23,25,18],
        "1 thessalonians":[10,20,13,18,28],
        "2 thessalonians":[12,17,18],
        "1 timothy":     [20,15,16,16,25,21],
        "2 timothy":     [18,26,17,22],
        "titus":         [16,15,15],
        "philemon":      [25],
        "hebrews":       [14,18,19,16,14,20,28,13,28,39,40,29,25],
        "james":         [27,26,18,17,20],
        "1 peter":       [25,25,22,19,14],
        "2 peter":       [21,22,18],
        "1 john":        [10,29,24,21,21],
        "2 john":        [13],
        "3 john":        [15],
        "jude":          [25],
        "revelation":    [20,29,22,11,14,17,17,13,21,11,19,17,18,20,8,21,18,24,21,15,27,21],
    }

    # Canonicalize the ref's book name (handles "1 Corinthians", "Song of Solomon", etc.)
    try:
        ref_parts   = ref.split()
        # ref format: "Book Name chapter:verse"  e.g. "Acts 8:29" or "1 Corinthians 10:13"
        # The last element is "chapter:verse"; everything before is the book.
        book_key    = " ".join(ref_parts[:-1]).lower().strip()
        chap_str, verse_str = ref_parts[-1].split(":")
        chap_num    = int(chap_str)
        verse_num   = int(verse_str.split()[0])

        counts = _CHAPTER_VERSE_COUNTS.get(book_key)
        if counts and 1 <= chap_num <= len(counts):
            max_verse = counts[chap_num - 1]
            if verse_num > max_verse:
                logger.info(
                    f"🚫 REJECTED: {ref} — chapter {chap_num} of {book_key.title()} "
                    f"only has {max_verse} verses (got v{verse_num})"
                )
                return True
    except (ValueError, IndexError, AttributeError):
        pass

    return False


def _is_range_not_verse(sentence: str, chap: str, verse: str) -> bool:
    """Bug Fix 3: Return True if the two numbers (chap, verse) represent a chapter
    range rather than a chapter:verse citation, so the fast-path does NOT present
    it as a verse.

    Two detection strategies are used:

    A) Digit-present path — the literal digits appear in the sentence and a range
       indicator word sits between them (handles English: "Daniel 1 through 6").

    B) Word-number path — the digits were produced by the parser normalising
       Malayalam/spoken number words (e.g. "ഒന്നു"→1, "ആറു"→6), so they may NOT
       appear literally in the raw sentence.  If ANY unambiguous range indicator is
       present AND both numbers are plausible chapter numbers (≤ 50), treat as range.
       (Verse numbers that large — e.g. Psalm 119:176 — would not appear in a normal
       chapter-range description.)"""
    # Strategy A: digit-literal check with range indicator between them
    for m_ch in re.finditer(rf'\b{re.escape(chap)}\b', sentence):
        cp = m_ch.end()
        for m_vs in re.finditer(rf'\b{re.escape(verse)}\b', sentence):
            vp = m_vs.start()
            if cp < vp:
                between = sentence[cp:vp]
                if _RANGE_INDICATOR_RE.search(between) or re.search(r'\s[-–]\s', between):
                    return True

    # Strategy B: spoken / Malayalam number-word path
    if _RANGE_INDICATOR_RE.search(sentence):
        try:
            if int(chap) <= 50 and int(verse) <= 50:
                return True
        except ValueError:
            pass

    return False

# ── Bug Fix 1: Book-count / money guard ─────────────────────────────────────
_BOOK_COUNT_RE = re.compile(
    r'\b(\d+)\s+(?:books?|episodes?|letters?|chapters?|times?|words?|'
    r'missionaries|journeys?|trips?|people|men|women|'
    r'dollars?|rupees?|cents?|paise?|\$|£|€|'
    r'percent|percentage|%|'
    r'members?|families|churches?|nations?|countries|'
    r'days?|weeks?|months?|years?|hours?|minutes?|'
    r'പുസ്തകങ്ങൾ|പുസ്തകം)',
    re.IGNORECASE
)

# Sentences that are clearly about money/offerings — a number here is NOT a verse
_MONEY_CONTEXT_RE = re.compile(
    r'\b(?:offer(?:ing)?s?|tithe|donation|collection|amount|'
    r'rupee|dollar|cent|paise|\$|£|€|'
    r'percent|percentage|%|'
    r'budget|fund|money|pay(?:ment)?|salary|'
    r'പ്രണ്ടിക്കൾ|കാണിക്ക|ദശാംശ)\b',
    re.IGNORECASE
)

def _is_book_count_number(text: str, num_str: str) -> bool:
    """Return True if num_str appears as a book-count or money quantity in text.
    e.g. 'the last three books' → '3' is a count, not a chapter number.
    e.g. '100 dollars offered' → '100' is money, not a verse."""
    for m in _BOOK_COUNT_RE.finditer(text):
        if m.group(1) == num_str:
            return True
    # If the sentence context is clearly about money/offerings, any large number is suspect
    if _MONEY_CONTEXT_RE.search(text):
        try:
            if int(num_str) >= 10:
                return True
        except ValueError:
            pass
    return False


# ── Bug Fix 2B: Ordinal-occasion guard ────────────────────────────────────────
_ORDINAL_OCCASION_RE = re.compile(
    r'\b(?:second|third|fourth|once\s+again|another)\s+(?:chance|time|opportunity|occasion)\b'
    r'|രണ്ടാമത്\s*(?:ഒരു\s+)?(?:അവസരം|തവണ)'
    r'|വീണ്ടും\s+(?:ഒരു\s+)?(?:അവസരം|തവണ)',
    re.IGNORECASE
)

def _strip_ordinal_occasions(text: str) -> str:
    """Remove 'second chance / third time / രണ്ടാമത് അവസരം' phrases from text
    before parsing so ordinals are not mistaken for chapter numbers."""
    return _ORDINAL_OCCASION_RE.sub(' ', text)


# ── Bug Fix 3B: John the Baptist guard ────────────────────────────────────────
def _is_john_the_baptist(text: str) -> bool:
    """Return True if 'John' in this text refers to John the Baptist, not the Gospel."""
    return bool(re.search(r'\bJohn\s+the\s+Baptist\b', text, re.IGNORECASE))


def _is_john_surname(text: str) -> bool:
    """Return True if 'John' in this text only appears as part of a 
    surname like Johnson, Johnston, Johnny — not as a standalone word."""
    # If "John" appears standalone (word boundary on both sides), it's legit
    if re.search(r'\bJohn\b', text, re.IGNORECASE):
        return False
    # "John" only appears embedded in a longer word (e.g. Johnson)
    if re.search(r'\bJohn\w+', text, re.IGNORECASE):
        return True
    return False


# ── Ambiguous-book-as-person guard ───────────────────────────────────────────
# Many Bible book names double as common personal names (John, Matthew, Mark,
# Luke, James, Ruth, Joel, Job, Amos, Jonah, Micah, Peter …).  Without an
# unambiguous chapter/verse signal these tokens must be treated as person or
# topic words, NOT as a book anchor or verse lookup trigger.

# Title/role words that can precede a person's name
_PERSON_TITLE_RE = re.compile(
    r'\b(?:'
    r'pastor|rev(?:erend)?|bishop|elder|deacon|minister|'
    r'apostle|prophet(?:ess)?|evangelist|preacher|teacher|'
    r'brother|bro|sister|sis|'
    r'dr|mr|mrs|ms|miss|mister|prof(?:essor)?|'
    r'saint|st'
    r')\b',
    re.IGNORECASE,
)

# Relational/descriptive suffixes that identify a person rather than a book
# e.g. "John the Baptist", "Joel the prophet", "Matthew the tax collector",
#       "Peter the apostle", "James the brother of the Lord"
_PERSON_SUFFIX_RE = re.compile(
    r'\b(?:'
    r'the\s+(?:baptist|prophet(?:ess)?|apostle|disciple|evangelist|elder|'
    r'tax\s+collector|zealot|son\s+of|brother\s+of|daughter\s+of|'
    r'king|priest|servant|scribe|pharisee|sadducee|'
    r'righteous|blessed|holy|great|good)'
    r'|(?:his|her|their|the)\s+(?:son|daughter|wife|mother|father|brother|sister|servant|disciple)'
    r'|said|spoke|answered|replied|wept|prayed|wrote|declared|preached'
    r'|\'s\s+(?:letter|gospel|epistle|vision|book|prophecy|account|narrative)'
    r')\b',
    re.IGNORECASE,
)

# Possessive/biographical patterns:  "John's mother",  "the ministry of Joel",
# "the book of Matthew" as narrative description (not an explicit reading command)
_PERSON_POSSESSIVE_RE = re.compile(
    r'\b(?:john|matthew|mark|luke|james|ruth|joel|job|amos|jonah|micah|peter|'
    r'jude|hosea|nahum|philemon|timothy|titus)\b'
    r'(?:\'s\b)',
    re.IGNORECASE,
)

# Dual-use tokens that require extra evidence before being treated as Bible books
_AMBIGUOUS_BOOK_TOKENS = frozenset({
    "john", "matthew", "mark", "luke", "james", "ruth",
    "joel", "job", "amos", "jonah", "micah", "peter",
    "jude", "hosea", "nahum", "philemon", "timothy", "titus",
})

# Evidence patterns that confirm a token IS being used as a Bible-book reference
# (chapter keyword, colon-verse notation, explicit reading command, or digit-after-name)
_BOOK_EVIDENCE_RE = re.compile(
    r'(?:'
    r'\b(?:chapter|chap|ch|verse|verses)\b'               # chapter/verse keyword
    r'|:\s*\d'                                             # colon-verse notation
    r'|\b(?:gospel|epistle|book|letter)\s+of\b'           # "gospel of John"
    r'|\b(?:open|turn|read(?:ing)?)\s+(?:your\s+)?bibles?' # reading command
    r'|\b(?:let[\'s]*\s+(?:now\s+)?read|I\s+will\s+read)'
    r')',
    re.IGNORECASE,
)


def _is_book_as_person(book_name: str, text: str) -> bool:
    """Return True if *book_name* appears in *text* as a person/topic reference
    rather than as a Bible-book anchor, making any verse lookup invalid.

    A token is treated as a person unless the text contains unambiguous
    book-reference evidence (chapter keyword, colon-verse, reading command,
    or a digit directly following the name).

    Rule priority (first match wins):
      1. A digit immediately follows the name  →  book reference (allow).
      2. A chapter/verse keyword or reading command is present  →  book reference (allow).
      3. A person-title prefix (Pastor John, Apostle Peter) is present  →  person (block).
      4. A person-suffix phrase (John the Baptist, Joel the prophet) is present  →  person (block).
      5. A possessive form (<name>'s) is present  →  person (block).
      6. Token is in _AMBIGUOUS_BOOK_TOKENS AND no book evidence → person (block).
    """
    if not book_name:
        return False
    token = book_name.strip().lower()
    if token not in _AMBIGUOUS_BOOK_TOKENS:
        return False  # unambiguous book name (e.g. Philippians, Revelation) — allow

    # Rule 1: digit immediately following the name → book reference
    if re.search(rf'\b{re.escape(book_name)}\s+\d', text, re.IGNORECASE):
        return False

    # Rule 2: chapter/verse keyword or reading command present → book reference
    if _BOOK_EVIDENCE_RE.search(text):
        return False

    # Rule 3: person-title prefix preceding the name
    m_title = _PERSON_TITLE_RE.search(text)
    if m_title:
        # Title must appear at or before the book-name token
        m_name = re.search(rf'\b{re.escape(book_name)}\b', text, re.IGNORECASE)
        if m_name and m_title.start() <= m_name.start():
            logger.debug(
                f"🚫 PERSON-GUARD: '{book_name}' preceded by title '{m_title.group(0)}'"
                f" in '{text[:80]}'"
            )
            return True

    # Rule 4: person-suffix phrase following the name
    m_name = re.search(rf'\b{re.escape(book_name)}\b', text, re.IGNORECASE)
    if m_name:
        suffix_window = text[m_name.end():m_name.end() + 60]
        if _PERSON_SUFFIX_RE.search(suffix_window):
            logger.debug(
                f"🚫 PERSON-GUARD: '{book_name}' followed by person-suffix"
                f" in '{text[:80]}'"
            )
            return True

    # Rule 5: possessive form
    if _PERSON_POSSESSIVE_RE.search(text):
        logger.debug(
            f"🚫 PERSON-GUARD: possessive form of '{book_name}'"
            f" in '{text[:80]}'"
        )
        return True

    # Rule 6: ambiguous token with no book evidence → default to person
    logger.debug(
        f"🚫 PERSON-GUARD (default): '{book_name}' in _AMBIGUOUS_BOOK_TOKENS"
        f" with no chapter/verse evidence in '{text[:80]}'"
    )
    return True


# ── Structural-impossibility check ───────────────────────────────────────────
# If the current anchor makes a parsed ref structurally impossible — e.g. the
# engine is at Matthew 28 and the parser returns Matthew 29 (which doesn't
# exist) — the ref is rejected outright.  No "nearby valid verse" substitution
# is attempted; silence is always preferable to a wrong presentation.

def _is_structurally_impossible(ref: str, text: str) -> bool:
    """Return True if *ref* is structurally impossible given what we know about
    the Bible's verse counts AND the current anchor context.

    This is a stronger form of _reject_verse_out_of_range:
      • _reject_verse_out_of_range checks only the ref itself (per-chapter table).
      • This function additionally checks whether the parsed chapter is plausible
        given the active anchor — e.g. a parser artefact producing Matthew 29
        when the active context is Matthew 28 (Matthew only has 28 chapters).

    Returns True (impossible) and logs the reason.  Returns False (plausible).
    No substitution is ever performed here; callers must drop the ref entirely.
    """
    if ":" not in ref:
        return False  # chapter-only refs are handled elsewhere
    try:
        ref_parts   = ref.split()
        book_key    = " ".join(ref_parts[:-1]).lower().strip()
        chap_str, verse_str = ref_parts[-1].split(":")
        chap_num    = int(chap_str)
        verse_num   = int(verse_str.split()[0])
    except (ValueError, IndexError):
        return False

    # Reuse the per-chapter table already defined in _reject_verse_out_of_range
    # (we access it inline to avoid code duplication)
    _CHAPTER_VERSE_COUNTS: dict = {
        "genesis":       [31,25,24,26,32,22,24,22,29,32,32,20,18,24,21,16,27,33,38,18,34,24,20,67,34,35,46,22,35,43,55,32,20,31,29,43,36,30,23,23,57,38,34,34,28,34,31,22,33,26],
        "job":           [22,13,26,21,27,30,21,22,35,22,20,25,28,22,35,22,16,21,29,29,34,30,17,25,6,14,23,28,25,31,40,22,33,37,16,33,24,41,30,24,34,17],
        "joel":          [20,32,21],
        "jonah":         [17,10,10,11],
        "matthew":       [25,23,17,25,48,34,29,34,38,42,30,50,58,36,39,28,27,35,30,34,46,46,39,51,46,75,66,20],
        "mark":          [45,28,35,41,43,56,37,38,50,52,33,44,37,72,47,20],
        "luke":          [80,52,38,44,39,49,50,56,62,42,54,59,35,35,32,31,37,43,48,47,38,71,56,53],
        "john":          [51,25,36,54,47,71,53,59,41,42,57,50,38,31,27,33,26,40,42,31,25],
        "acts":          [26,47,26,37,42,15,60,40,43,48,30,25,52,28,41,40,34,28,41,38,40,30,35,27,27,32,44,31],
        "romans":        [32,29,31,25,21,23,25,39,33,21,36,21,14,23,33,27],
        "revelation":    [20,29,22,11,14,17,17,13,21,11,19,17,18,20,8,21,18,24,21,15,27,21],
        "ruth":          [22,23,18,22],
        "hosea":         [11,23,5,19,15,11,16,14,17,15,12,14,16,9],
        "amos":          [15,16,15,13,27,14,17,14,15],
        "micah":         [16,13,12,13,15,16,20],
        "nahum":         [15,13,19],
        "philemon":      [25],
        "james":         [27,26,18,17,20],
        "1 peter":       [25,25,22,19,14],
        "2 peter":       [21,22,18],
        "1 john":        [10,29,24,21,21],
        "2 john":        [13],
        "3 john":        [15],
        "jude":          [25],
        "1 timothy":     [20,15,16,16,25,21],
        "2 timothy":     [18,26,17,22],
        "titus":         [16,15,15],
    }

    counts = _CHAPTER_VERSE_COUNTS.get(book_key)

    # 1. Chapter exceeds total chapters for the book
    if counts and chap_num > len(counts):
        logger.info(
            f"🚫 STRUCTURALLY IMPOSSIBLE: {ref} — {book_key.title()} only has "
            f"{len(counts)} chapter(s) (got ch{chap_num}); dropping without substitution"
        )
        return True

    # 2. Verse exceeds the chapter's verse count
    if counts and 1 <= chap_num <= len(counts):
        max_v = counts[chap_num - 1]
        if verse_num > max_v:
            logger.info(
                f"🚫 STRUCTURALLY IMPOSSIBLE: {ref} — {book_key.title()} {chap_num} "
                f"only has {max_v} verses (got v{verse_num}); dropping without substitution"
            )
            return True

    # 3. Active anchor contradicts the parsed chapter (parser artefact)
    #    Only fire when: same book, explicit anchor, chapter clearly wrong,
    #    AND no chapter keyword in text (so "Matthew chapter 5" is never blocked).
    if (current_book and current_chapter and
            book_key == current_book.lower() and
            not re.search(r'\b(?:chapter|chap|ch)\b', text, re.IGNORECASE)):
        try:
            anchor_ch = int(current_chapter)
            # Block if the parsed chapter is more than 2 ahead of the anchor
            # with no forward-advance evidence, or simply non-existent for the book
            if counts and chap_num > len(counts):
                logger.info(
                    f"🚫 STRUCTURALLY IMPOSSIBLE (anchor): {ref} — anchor "
                    f"{current_book} {current_chapter}, parsed ch{chap_num} doesn't exist"
                )
                return True
        except ValueError:
            pass

    return False

def detect_verse_hybrid(text, controller, confidence=1.0, parser=None) -> bool:
    # NOTE: WORSHIP_MODE does NOT bail here — detection runs fully for debug logging.
    # The display gate is inside send_verse / VerseController.send_verse.
    global current_book, current_chapter, current_verse, _last_explicit_ref_time

    if not text or len(text.strip()) < 3:
        return False

    fixes = {
        r"\b(?:sam's|sams|sam)\b": "psalms",
        r"\bnayan\b":              "nine",
    }
    for pattern, replacement in fixes.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    # Bug ML-2 fix: Sarvam STT (Malayalam) often emits English number words mid-transcript,
    # e.g. "verse Eight disobedient people" instead of "verse 8".
    # SPOKEN_NUMERAL_MODE handles Malayalam numeral words but not English ones.
    # Replace English cardinal/ordinal words with digits before any parser sees the text.
    if SPOKEN_NUMERAL_MODE and USE_SARVAM:
        _ML2_EN_NUMS = {
            "zero":"0","one":"1","two":"2","three":"3","four":"4","five":"5",
            "six":"6","seven":"7","eight":"8","nine":"9","ten":"10",
            "eleven":"11","twelve":"12","thirteen":"13","fourteen":"14",
            "fifteen":"15","sixteen":"16","seventeen":"17","eighteen":"18",
            "nineteen":"19","twenty":"20","twenty one":"21","twenty two":"22",
            "twenty three":"23","twenty four":"24","twenty five":"25",
            "twenty six":"26","twenty seven":"27","twenty eight":"28",
            "twenty nine":"29","thirty":"30",
            # ordinal forms that Sarvam/Deepgram sometimes emits
            "first":"1","second":"2","third":"3","fourth":"4","fifth":"5",
            "sixth":"6","seventh":"7","eighth":"8","ninth":"9","tenth":"10",
            "eleventh":"11","twelfth":"12","thirteenth":"13","fourteenth":"14",
            "fifteenth":"15","sixteenth":"16","seventeenth":"17","eighteenth":"18",
            "nineteenth":"19","twentieth":"20",
        }
        _ml2_re = re.compile(
            r'\b(' + '|'.join(re.escape(k) for k in sorted(_ML2_EN_NUMS, key=len, reverse=True)) + r')\b',
            re.IGNORECASE
        )
        text = _ml2_re.sub(lambda m: _ML2_EN_NUMS[m.group(1).lower()], text)

    def trigger_onwards_if_needed(ref_string, original_text):
        if any(kw in original_text.lower() for kw in ONWARDS_KEYWORDS):
            parts = ref_string.split()
            if ":" in parts[-1]:
                ch, vs = parts[-1].split(":")
                bk     = " ".join(parts[:-1])
                # Bug 1: Override with current context if parser resolved a different book/chapter
                if current_book and current_chapter:
                    if bk != current_book or ch != current_chapter:
                        logger.warning(
                            f"⚠️ ONWARDS context override: parser said {bk} {ch}:{vs}, "
                            f"but active context is {current_book} {current_chapter} — using context"
                        )
                        bk = current_book
                        ch = current_chapter
                _start_onwards(bk, ch, vs)

    try:
        _apply_book_context_if_mentioned(text)
        if check_verse_queue(text, controller):
            return True
        if _check_onwards_advance(text, controller):
            return True
        # If Verse Interrupt is on, we may be waiting for speaker to say the verse
        if VERSE_INTERRUPT_ENABLED and check_vtc(text, controller):
            return True

        num_norm = normalize_numbers_only(text)
        
        # Bug 2: Suppress compound numbers like "hundred and fifty" to prevent false positives
        # When a number is part of a compound (preceded by magnitude words), ignore it
        compound_pattern = re.compile(
            r'\b(?:hundred|thousand|million|billion)\s+and\s+(\d{1,3})\b',
            re.IGNORECASE
        )
        if compound_pattern.search(num_norm):
            # If we find a compound number, skip number extraction for this text
            logger.debug("Compound number detected - suppressing number extraction")
            num_norm = re.sub(r'\b\d{1,3}\b', '', num_norm)  # Remove all digits
        
        num_norm = re.sub(
            r'\b(20|30|40|50|60|70|80|90)\s+([1-9])\b',
            lambda m: str(int(m.group(1)) + int(m.group(2))),
            num_norm,
        )
        # Bug 6: "X and Y" → "X:Y" in num_norm so Layer 2+ can detect spoken chapter:verse
        num_norm = re.sub(r'\b(\d{1,3})\s+and\s+(\d{1,3})\b', r'\1:\2', num_norm)

        # Context helper — if we already know the book, allow "chapter 3" / "ch 3" to set
        # (or UPDATE) the chapter context.  Previously this only fired when current_chapter
        # was None, so a preacher saying "that's what happens in chapter 8" while the context
        # was still stuck on chapter 6 would never advance.
        # Bug 3 fix: run whenever current_book is set, regardless of whether current_chapter
        # already has a value.  A safety check prevents nonsensical backward jumps.
        if current_book:
            m_ch = re.search(r'\b(?:chapter|chap|ch)\s+(\d{1,3})\b', num_norm.lower())
            if m_ch:
                proposed_chapter = m_ch.group(1)
                # Issue 1 fix: Reject a chapter that is suspiciously lower than the session
                # high-water mark for this book.  "chapter nine" in a Revelation 19 sermon
                # is almost always a mishear of "chapter nineteen" — don't let a low chapter
                # number silently clobber a chapter we've already progressed past.
                _best_hw_for_book = max(
                    (v for k, v in _session_verse_high_water.items()
                     if k.startswith(current_book + " ")),
                    default=0,
                )
                _best_hw_chapter = 0
                for k in _session_verse_high_water:
                    if k.startswith(current_book + " "):
                        try:
                            _best_hw_chapter = max(_best_hw_chapter, int(k.split()[-1]))
                        except ValueError:
                            pass
                if _best_hw_chapter > 0 and int(proposed_chapter) < _best_hw_chapter - 2:
                    logger.warning(
                        f"⚠️ Chapter downgrade blocked: '{current_book} {proposed_chapter}' "
                        f"contradicts session high-water chapter {_best_hw_chapter} — "
                        f"likely mishear (e.g. 'nine' for 'nineteen')"
                    )
                elif current_chapter == proposed_chapter:
                    pass  # already set — no-op, avoid noisy log spam
                else:
                    old_ch = current_chapter
                    current_chapter = proposed_chapter
                    current_verse   = None
                    if old_ch is None:
                        logger.info(f"📌 Chapter context set: {current_book} {current_chapter}")
                    else:
                        logger.info(f"📌 Chapter context updated: {current_book} {old_ch} → {current_chapter} (narrative mention)")

        # Bug 5: Log and skip if text is purely a chapter/verse range description
        _range_desc = re.search(
            r'\b(?:chapters?|verses?)\s+\d+\s+(?:to|through|thru)\s+\d+\b',
            num_norm, re.IGNORECASE,
        )
        if _range_desc and not re.search(r'\b(?:verse|verses)\s+\d+\s*[:\-]', num_norm):
            # Bug 1: latch to prevent repeated RANGE_DETECTED on same passage
            global _range_latch_active, _range_latch_ref
            current_ref = f"{current_book} {current_chapter}" if current_book and current_chapter else None
            if _range_latch_active and _range_latch_ref == current_ref:
                # Already logged a range for this passage, skip
                pass
            else:
                logger.info(f"📋 RANGE_DETECTED (suppressed): {_range_desc.group()}")
                _range_latch_active = True
                _range_latch_ref = current_ref

        # Layer 0 — "Next Verse" command
        if current_book and current_chapter and current_verse:
            if re.search(r'\bnext\s+verse\b', text, re.IGNORECASE):
                # Do not fire if followed by an explicit number (e.g. "next verse fourteen")
                if not re.search(r'\bnext\s+verse\s+\d+\b', num_norm.lower(), re.IGNORECASE):
                    next_v = int(current_verse) + 1
                    ref = f"{current_book} {current_chapter}:{next_v}"
                    logger.info(f"🔍 NEXT VERSE: {ref} (100% Acc)")
                    deliver_verse(ref, controller, bypass_cooldown=True, confidence=1.0, source="NEXT VERSE")
                    trigger_onwards_if_needed(ref, text)
                    return True

        # BUG 5: Intercept multi-verse listings BEFORE Layer 1 parser
        # If there are 3+ numbers, no "chapter" keyword, and "verse" keyword is present
        # AND we have active book/chapter context -> force skip Layer 1 so Layer 2 handles it safely
        is_multi_verse_list = False
        if current_book and current_chapter:
            all_digits = re.findall(r'\b(\d{1,3})\b', num_norm)
            has_verse_kw = re.search(r'\b(?:verse|verses)\b', text, re.IGNORECASE)
            has_chap_kw  = re.search(r'\b(?:chapter|chap|ch)\b', text, re.IGNORECASE)
            if len(all_digits) >= 3 and has_verse_kw and not has_chap_kw:
                is_multi_verse_list = True

        # Bug Fix 2B: strip ordinal-occasion phrases before re-parsing
        text_for_parser = _strip_ordinal_occasions(text)
        _active_parser = parser or PRIMARY_PARSER
        refs = [] if is_multi_verse_list else _active_parser(text_for_parser)
        if refs:
            verse      = refs[0]
            is_blocked = False
            
            # BUG 3: Unconditional Revelation guard (blocks "revelation" in commentary)
            if "Revelation" in verse:
                _ml_chars  = sum(1 for c in text if '\u0D00' <= c <= '\u0D7F')
                _nospace    = len(text.replace(' ', ''))
                _is_ml_ctx  = _nospace > 0 and (_ml_chars / _nospace) > 0.40
                if _is_ml_ctx:
                    # Malayalam-dominant context — allow ONLY when "revelation" appears
                    # explicitly as an English word followed by a chapter number.
                    # This lets the preacher say "Revelation 13:8" in a Malayalam
                    # sermon without being blocked.  Generic transliteration noise
                    # ("വെളിപ്പാട്" etc.) will still be blocked.
                    _has_explicit_rev = bool(
                        re.search(r'\brevelation\s+\d+\b', text, re.IGNORECASE) or
                        re.search(r'\bbook\s+of\s+revelation\b', text, re.IGNORECASE)
                    )
                    if not _has_explicit_rev:
                        logger.debug(f"🚫 Revelation detection skipped: >40% Malayalam context in '{text[:60]}'")
                        is_blocked = True
                elif not re.search(r'\brevelation\b', text, re.IGNORECASE):
                    # "Revelation" does not appear as an isolated English word at all
                    if _dedup_blocked(text, "revelation"):
                        logger.info(f"\U0001f6ab BLOCKED: 'Revelation' not a standalone English word in '{text[:60]}'")
                    is_blocked = True
                elif not (re.search(r'\bbook\s+of\s+revelation\b', text, re.IGNORECASE) or
                          re.search(r'\brevelation\s+(?:chapters?|chap|ch)\b', text, re.IGNORECASE) or
                          re.search(r'\brevelation\s+\d+\b', text, re.IGNORECASE)):
                    # Standalone "Revelation" without chapter/explicit phrasing
                    if _dedup_blocked(text, "revelation"):
                        logger.info(f"\U0001f6ab BLOCKED: 'Revelation' without chapter/explicit phrasing in '{text[:60]}'")
                    is_blocked = True

            # BUG 4: Unconditional Numbers guard (blocks bare numbers words mapped to book)
            if "Numbers " in verse:  # Note trailing space to only match the book "Numbers N"
                if not (re.search(r'\bNumbers\s+(?:chapter|chap|ch)\b', text, re.IGNORECASE) or
                        re.search(r'\bNumbers\s+\d+\b', text) or
                        re.search(r'\bbook\s+of\s+numbers\b', text, re.IGNORECASE)):
                    if _dedup_blocked(text, "numbers"):
                        logger.info(f"\U0001f6ab BLOCKED: 'Numbers' without chapter/explicit phrasing in '{text[:60]}'")
                    is_blocked = True

            # Bug 5: Require an explicit anchor — a book name, chapter/verse keyword, or colon.
            # A bare digit from casual speech ("one more thing", "three reasons") is not sufficient.
            has_ref_anchor = bool(
                re.search(r'\b(?:chapter|chap|ch|verse|verses)\b', text, re.IGNORECASE)
                or ':' in text
                or any(kw in text.lower() for kw in BOOK_KEYWORDS)
            )
            
            if not has_ref_anchor:
                # Issue 4 fix: a long utterance (≥8 words) with no anchor is still worth
                # sending to the LLM if we have active book context and a recent explicit
                # ref — it may be a near-verbatim verse quote (e.g. Psalm 19:14).
                # We skip the BLOCKED log and fall through to the LLM layer instead.
                _is_long_quote_candidate = (
                    len(text.split()) >= 8
                    and current_book
                    and current_chapter
                    and (time.time() - _last_explicit_ref_time) < _EXPLICIT_REF_EXPIRY
                )
                if not _is_long_quote_candidate:
                    if _dedup_blocked(text, "no-anchor"):
                        logger.info(f"\U0001f6ab BLOCKED: No book/chapter/verse anchor in '{text[:60]}'")
                    is_blocked = True
            if not is_blocked:
                is_blocked = _reject_verse_out_of_range(verse)
            
            if not is_blocked:
                # Bug : Proper Name False Positive Guard (e.g. "Evangelist Daniel")
                person_prefixes = r"(?:pastor|evangelist|brother|bro|sister|sis|prophet|apostle|reverend|rev|bishop|dr|mr|mrs|mister|miss|ms|minister)"
                book_kw_pattern = '|'.join(re.escape(kw) for kw in sorted(BOOK_KEYWORDS, key=len, reverse=True))
                name_guard_re = re.compile(rf'\b{person_prefixes}\b(?:\s+[a-z\.]+){{0,3}}\s+({book_kw_pattern})\b', re.IGNORECASE)
                
                for m_person in name_guard_re.finditer(text):
                    book_kw_start = m_person.start(1)
                    book_kw_end = m_person.end(1)
                    text_without_name = text[:book_kw_start] + text[book_kw_end:]
                    
                    if verse not in _active_parser(text_without_name):
                        logger.info(f"🚫 BLOCKED Layer 1 False Positive: {verse} (Person Name Prefix: '{m_person.group(0).strip()}')")
                        is_blocked = True
                        break

            if not is_blocked:
                # Bug Fix 1: Block chapter refs where the chapter number is a book-count
                # e.g. "Deuteronomy...the last three books" → Deuteronomy 3 is wrong
                chap_token = verse.split()[-1].split(":")[0]
                if _is_book_count_number(text, chap_token):
                    logger.info(f"🚫 BLOCKED: {verse} — chapter number is a book-count in '{text[:60]}'")
                    is_blocked = True

            if not is_blocked:
                # Bug Fix 2A (extended): Verse-keyword takes priority over chapter interpretation.
                #
                # If the text contains an explicit verse keyword ("verse", "verses", Malayalam
                # equivalents) AND we have an active book+chapter anchor, the spoken number is
                # almost certainly a verse, not a chapter transition.  Block the Layer 1 result
                # and let Layer 2 resolve it as current_chapter:N.
                #
                # Two sub-cases are handled:
                #
                # Sub-case A — chapter-only ref (no colon in parsed result, e.g. "Daniel 8"):
                #   Block whenever verse keyword is present + same book, regardless of whether
                #   the parsed chapter number matches current_chapter.  The old guard
                #   `chap_token != current_chapter` missed the case where the chapter number
                #   equals the active chapter (speaker says "verse eight" in Daniel 8 context
                #   → parser returns "Daniel 8" → must still block so Layer 2 gives Daniel 8:8).
                #
                # Sub-case B — full ref with DIFFERENT chapter (colon present, e.g. "Daniel 2:8"
                #   when Daniel 12 is active):
                #   If the text has a verse keyword but NO chapter keyword ("chapter", "chap", "ch"),
                #   the parser likely grabbed a stale book+chapter from the text blob.  Block it so
                #   Layer 2 resolves the verse number against the active chapter instead.
                #   Explicit "Daniel chapter 8 verse 3" is protected by the has_chapter_kw guard.
                if current_book and current_chapter:
                    _has_verse_kw  = re.search(r'\b(?:verse|verses)\b|വാക്യ|വചന', text, re.IGNORECASE)
                    _has_chap_kw   = re.search(r'\b(?:chapter|chap|ch)\b', text, re.IGNORECASE)
                    _ref_book      = " ".join(verse.split()[:-1]).strip()
                    # strip verse part for both chapter-only and full refs
                    if ":" in verse:
                        _parts_v   = verse.split()
                        _ref_book  = " ".join(_parts_v[:-1]).strip()
                        _parsed_ch = _parts_v[-1].split(":")[0]
                    else:
                        _parsed_ch = verse.split()[-1]
                    _same_book = (_ref_book.lower() == (current_book or "").lower())

                    if _has_verse_kw and _same_book and not _has_chap_kw:
                        try:
                            _parsed_ch_int = int(_parsed_ch)
                            if ":" not in verse:
                                # Sub-case A: chapter-only ref + verse keyword → always block
                                logger.info(
                                    f"🚫 BLOCKED (2A-chap): {verse} — chapter-only ref with verse keyword; "
                                    f"anchor={current_book} {current_chapter} → Layer 2 will resolve verse"
                                )
                                is_blocked = True
                            elif _parsed_ch != current_chapter and _parsed_ch_int <= 150:
                                # Sub-case B: full ref with different chapter + verse keyword → block
                                logger.info(
                                    f"🚫 BLOCKED (2A-full): {verse} — full ref chapter {_parsed_ch} differs "
                                    f"from anchor chapter {current_chapter}; verse keyword present but no "
                                    f"chapter keyword → Layer 2 will resolve verse in active chapter"
                                )
                                is_blocked = True
                            else:
                                logger.debug(
                                    f"✅ ALLOWED (2A): {verse} — same chapter or chapter keyword present; "
                                    f"anchor={current_book} {current_chapter}"
                                )
                        except ValueError:
                            pass

            if not is_blocked:
                # Unified ambiguous-book-as-person guard (covers John, Matthew, Mark,
                # Luke, James, Ruth, Joel, Job, Amos, Jonah, Micah, Peter, Jude, …).
                # Replaces the old "John the Baptist" + "John gospel cue" pair with a
                # single call that applies the same logic to all dual-use name tokens.
                _ref_book_token = " ".join(verse.split()[:-1]).strip() if ":" in verse else " ".join(verse.split())
                # Take just the last word of the book name for single-word books
                _book_last_word = _ref_book_token.split()[-1] if _ref_book_token else ""
                if _is_book_as_person(_book_last_word, text):
                    if _dedup_blocked(text, f"person-guard-{_book_last_word.lower()}"):
                        logger.info(
                            f"🚫 BLOCKED (person-guard): '{verse}' — "
                            f"'{_book_last_word}' treated as person/topic name in '{text[:80]}'"
                        )
                    is_blocked = True

            if not is_blocked:
                # Structural-impossibility check — verse/chapter doesn't exist for this book.
                # Unlike _reject_verse_out_of_range (which already ran above), this also
                # considers anchor context and logs explicitly that NO substitution is made.
                if _is_structurally_impossible(verse, text):
                    is_blocked = True

            if not is_blocked:
                chap_num = verse.split()[-1]
                blockers = [
                    "days", "weeks", "months", "years", "minutes", "hours",
                    "people", "men", "women", "points", "dollars",
                ]
                # Don't block legit "Book chapter N" just because "N days" appears nearby.
                is_explicit_chapter = bool(re.search(rf'\b(?:chapter|chap|ch)\s+{re.escape(chap_num)}\b', num_norm.lower()))
                if (not is_explicit_chapter) and any(re.search(rf'\b{chap_num}\s+{b}\b', num_norm) for b in blockers):
                    logger.info(f"🚫 BLOCKED Layer 1 False Positive: {verse} (Time/People phrase)")
                    is_blocked = True
            if not is_blocked:
                # Bug 1 fix: Narrative-reading guard — block a book-switch caused by a
                # third-person narrative phrase ("he was reading Isaiah 53").  Only apply
                # when the parsed ref is in a DIFFERENT book than the active context;
                # same-book refs are unaffected.
                if current_book:
                    _parsed_book = " ".join(verse.split()[:-1]) if ":" in verse else " ".join(verse.split()[:-1])
                    if _parsed_book.lower() != current_book.lower():
                        if _is_narrative_reading_context(text, _parsed_book):
                            logger.info(f"🚫 BLOCKED Layer 1 (narrative reading): '{verse}' — active context stays {current_book} {current_chapter}")
                            is_blocked = True
            if not is_blocked:
                logger.info(f"🔍 PARSER: {verse} ({int(confidence*100)}% Acc)")
                deliver_verse(verse, controller, bypass_cooldown=False, confidence=confidence, source="PARSER")
                _last_explicit_ref_time = time.time()
                trigger_onwards_if_needed(verse, text)
                if ":" in verse:
                    check_and_queue_range(text, verse, controller)
                return True

        # Fix 12: Verse range → capture first verse ("verses 7 8 9" or "verse 7 to 9")
        m_range_first = re.search(
            r'\\bverse[s]?\\s+(\\d{1,3})(?:\\s+(?:to|through|thru|and)\\s+\\d+|(?:\\s+\\d+){1,4})',
            num_norm, re.IGNORECASE
        )
        if m_range_first and current_book and current_chapter:
            first_v = m_range_first.group(1)
            ref = f"{current_book} {current_chapter}:{first_v}"
            logger.info(f"\U0001f50d VERSE-RANGE-FIRST: {ref} (first verse of range)")
            deliver_verse(ref, controller, bypass_cooldown=False,
                          confidence=confidence, source="VERSE-RANGE-FIRST")
            return True

        # VERSE-OF-CHAPTER (e.g. "verse 13 of 25")
        m_vof = re.search(
            r'\\bverse\\s+(\\d{1,3})\\s+of\\s+(?:chapter\\s+)?(\\d{1,3})\\b',
            num_norm, re.IGNORECASE
        )
        if m_vof and current_book:
            verse_n = m_vof.group(1)
            chap_n = m_vof.group(2)
            ref = f"{current_book} {chap_n}:{verse_n}"
            logger.info(f"🔍 VERSE-OF-CHAPTER: {ref} (100% Acc)")
            deliver_verse(ref, controller, bypass_cooldown=False,
                          confidence=confidence, source="VERSE-OF-CHAPTER")
            return True

        # Layer 2 — contextual (number only, same book/chapter)
        # Use _get_contextual_anchor() so "verse N" prefers the sermon anchor
        # over any active cross-reference overlay.
        _ctx_book, _ctx_chapter, _ctx_verse = _get_contextual_anchor()
        if _ctx_book and _ctx_chapter:
            text_lower = num_norm.lower()
            # Issue 5: Check if multiple numbers appear in a short phrase
            all_numbers = re.findall(r'\b(\d{1,3})\b', num_norm)
            has_multiple_numbers = len(all_numbers) > 1
            
            # Bug 3: Prioritise explicit "verse N" keyword so the verse digit is never confused
            # with an earlier number in the blob (e.g. "number two" → "2" earlier in the text).
            m_vkw = re.search(r'\b(?:verse|verses)\s+(\d{1,3})\b', text_lower)
            
            # Issue 5: If multiple numbers, only allow with explicit verse keyword
            if has_multiple_numbers and not m_vkw:
                logger.debug(f"🚫 Multiple numbers without verse keyword - ignoring: '{text[:60]}'")
                return False
            
            if m_vkw:
                candidate = m_vkw.group(1)
                # Bug ML-3 fix: reject backward jumps > 5 verses unless the speaker
                # explicitly signals going back (e.g. "let's go back to verse 1").
                # This prevents the LLM/contextual path from jumping to Hosea 4:1
                # when the sermon has already progressed to verse 17+.
                _ctx_key = f"{_ctx_book} {_ctx_chapter}"
                _explicit_backward = bool(re.search(
                    r'\b(?:go(?:ing)?\s+back|let\s*[\'s]*\s*(?:go\s+)?back|return\s+to|'
                    r'back\s+to\s+verse|revisit|re-?read|again\s+from)\b',
                    text_lower))
                # ── Contextual-floor bypass checks ──
                _floor_bypass_reason = None
                if CONTEXT_FLOOR_EXPLICIT_BYPASS and _is_explicit_full_ref(text):
                    _floor_bypass_reason = "explicit full ref (book+chapter+verse) in transcript"
                # NOTE: The old CONTEXT_FLOOR_MANUAL_CONTEXT_BYPASS floor-lowering
                # branch has been removed.  Manual context events are now metadata
                # only; they open a quarantine (checked in deliver_verse) rather
                # than lowering the detection floor here.
                elif _sermon_anchor_book and _ctx_key == f"{_sermon_anchor_book} {_sermon_anchor_chapter}":
                    # ── Same-chapter sermon-anchor bypass (this fix) ──────────
                    # When the speaker uses clear verse wording ("verse ten",
                    # "look at verse nine") AND we have an active sermon anchor
                    # in this exact chapter, treat same-chapter backreferences as
                    # intentional.  The floor still blocks bare random numbers
                    # (bare-digit path below) — only the keyword path gets this.
                    _STRONG_VERSE_RE = re.compile(
                        r'\b(?:look\s+at\s+verse|read\s+verse|see\s+verse|'
                        r'at\s+verse|in\s+verse|the\s+verse|verse\s+says?|'
                        r'verse)\s+(?:\d|one|two|three|four|five|six|seven|eight|nine|ten|'
                        r'eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|'
                        r'eighteen|nineteen|twenty|thirty|forty|fifty)',
                        re.IGNORECASE,
                    )
                    # Search both raw text and num_norm so "verse nine" and "verse 9" both match
                    if _STRONG_VERSE_RE.search(text) or _STRONG_VERSE_RE.search(num_norm):
                        _floor_bypass_reason = (
                            f"explicit verse keyword + active sermon anchor "
                            f"({_sermon_anchor_book} {_sermon_anchor_chapter}) — "
                            f"same-chapter backreference allowed"
                        )
                if (not _explicit_backward
                        and _last_presented_verse_book_chap == _ctx_key
                        and _last_presented_verse_num > 0
                        and int(candidate) < _last_presented_verse_num - 5):
                    if _floor_bypass_reason:
                        logger.info(
                            f"✅ CONTEXTUAL FLOOR bypassed for {_ctx_book} {_ctx_chapter}:{candidate} "
                            f"— {_floor_bypass_reason} "
                            f"(anchor={_ctx_book} {_ctx_chapter}, "
                            f"candidate=v{candidate}, last_presented=v{_last_presented_verse_num})"
                        )
                    else:
                        logger.info(
                            f"🚫 CONTEXTUAL FLOOR (ML-3): {_ctx_book} {_ctx_chapter}:{candidate} "
                            f"rejected — too far back "
                            f"(anchor={_ctx_book} {_ctx_chapter}, "
                            f"candidate=v{candidate}, last_presented=v{_last_presented_verse_num}, "
                            f"floor=v{_last_presented_verse_num - 5}); "
                            f"no strong verse keyword or sermon-anchor match — floor enforced"
                        )
                        return False
                ref = f"{_ctx_book} {_ctx_chapter}:{candidate}"
                logger.info(f"🔍 CONTEXTUAL: {ref} ({int(confidence*100)}% Acc) "
                            f"[anchor={_ctx_book} {_ctx_chapter}, floor rule: "
                            f"{'bypassed: ' + _floor_bypass_reason if _floor_bypass_reason else 'passed normally'}]")
                deliver_verse(ref, controller, bypass_cooldown=False, confidence=confidence, source="CONTEXTUAL")
                trigger_onwards_if_needed(ref, text)
                check_and_queue_range(num_norm, ref, controller)
                return True
            
            # Fallback: bare digit — only for short utterances or other explicit patterns
            m = re.search(r'\b(\d+)\b', num_norm)
            if m:
                candidate = m.group(1)
                is_valid  = False
                if len(text.split()) <= 2:
                    is_valid = True
                elif re.search(r'\b(?:v|vs)\s+' + candidate + r'\b', text_lower):
                    is_valid = True
                elif re.search(r'\b' + re.escape(candidate) + r'\s*(?:st|nd|rd|th)?\s+verse\b', text_lower):
                    is_valid = True
                elif re.search(r'\b(?:back|return|going)\b', text_lower) and re.search(r'\bverse\b', text_lower):
                    is_valid = True
                elif any(kw in text_lower for kw in ["വാക്യം", "വചനം", "വചന", "वचन", "पद"]):
                    is_valid = True
                if is_valid:
                    # Bug ML-3 fix: apply the same backward-jump floor to bare-digit path.
                    # Bare digits are the most likely to produce spurious low verse numbers.
                    _ctx_key2 = f"{_ctx_book} {_ctx_chapter}"
                    _explicit_bwd2 = bool(re.search(
                        r'\b(?:go(?:ing)?\s+back|let\s*[\'s]*\s*(?:go\s+)?back|return\s+to|'
                        r'back\s+to\s+verse|revisit|re-?read|again\s+from)\b',
                        text_lower))
                    # ── Contextual-floor bypass checks (bare-digit path) ──
                    _floor_bypass_reason2 = None
                    if CONTEXT_FLOOR_EXPLICIT_BYPASS and _is_explicit_full_ref(text):
                        _floor_bypass_reason2 = "explicit full ref (book+chapter+verse) in transcript"
                    # NOTE: The old CONTEXT_FLOOR_MANUAL_CONTEXT_BYPASS branch
                    # has been removed from the bare-digit path.  Manual/system
                    # context events open a quarantine (checked in deliver_verse)
                    # and must not lower the backward-jump floor here — bare
                    # digits are the highest false-positive risk and need the
                    # strongest protection during a quarantine window.
                    if (not _explicit_bwd2
                            and _last_presented_verse_book_chap == _ctx_key2
                            and _last_presented_verse_num > 0
                            and int(candidate) < _last_presented_verse_num - 5):
                        if _floor_bypass_reason2:
                            logger.info(
                                f"✅ CONTEXTUAL FLOOR bypassed (bare) for {_ctx_book} {_ctx_chapter}:{candidate} "
                                f"— {_floor_bypass_reason2}"
                            )
                        else:
                            logger.info(
                                f"🚫 CONTEXTUAL FLOOR (ML-3 bare): {_ctx_book} {_ctx_chapter}:{candidate} "
                                f"rejected — too far back (last presented v{_last_presented_verse_num}); "
                                f"bare digits are the highest false-positive risk — floor enforced"
                            )
                            return False
                    ref = f"{_ctx_book} {_ctx_chapter}:{candidate}"
                    logger.info(f"🔍 CONTEXTUAL: {ref} ({int(confidence*100)}% Acc)")
                    deliver_verse(ref, controller, bypass_cooldown=False, confidence=confidence, source="CONTEXTUAL")
                    trigger_onwards_if_needed(ref, text)
                    check_and_queue_range(num_norm, ref, controller)
                    return True

        # Layer 3 — Hindi devanagari digits
        m_hi = re.search(r'([\u0966-\u096F]+)', text)
        if m_hi and _ctx_book and _ctx_chapter:
            ref = f"{_ctx_book} {_ctx_chapter}:{m_hi.group(1)}"
            logger.info(f"🔍 HINDI CTX: {ref} ({int(confidence*100)}% Acc)")
            deliver_verse(ref, controller, bypass_cooldown=False, confidence=confidence, source="CONTEXTUAL")
            trigger_onwards_if_needed(ref, text)
            return True

        # Layer 4 — Malayalam digits
        m_ml = re.search(r'([\u0D66-\u0D6F]+)', text)
        if m_ml and _ctx_book and _ctx_chapter:
            ref = f"{_ctx_book} {_ctx_chapter}:{m_ml.group(1)}"
            logger.info(f"🔍 MALAYALAM CTX: {ref} ({int(confidence*100)}% Acc)")
            deliver_verse(ref, controller, bypass_cooldown=False, confidence=confidence, source="CONTEXTUAL")
            trigger_onwards_if_needed(ref, text)
            return True

        # Layer 5 — sequential (next verse)
        if _ctx_book and _ctx_chapter and _ctx_verse:
            m_num = re.search(r'\b(\d{1,3})\b', num_norm)
            if m_num:
                candidate = m_num.group(1)
                try:
                    if int(candidate) == int(_ctx_verse) + 1:
                        # Issue 3 fix: don't fire sequential on quantity phrases like
                        # "ten minutes", "ten points", "ten seconds", etc.
                        # Scan 3 tokens after the matched number for blocker words.
                        _seq_after = num_norm[m_num.end():].strip().split()
                        _SEQ_BLOCKERS = {
                            "minutes", "minute", "seconds", "second", "hours", "hour",
                            "days", "day", "weeks", "week", "months", "month", "years", "year",
                            "points", "point", "reasons", "reason", "things", "thing",
                            "times", "people", "men", "women", "dollars", "percent",
                            "members", "steps", "ways", "items", "chapters", "churches",
                        }
                        _seq_nearby = {w.lower().rstrip(".,!?;:") for w in _seq_after[:3]}
                        if _seq_nearby & _SEQ_BLOCKERS:
                            logger.debug(
                                f"🚫 SEQUENTIAL suppressed: '{candidate}' followed by "
                                f"quantity word in '{text[:60]}'"
                            )
                        else:
                            ref = f"{_ctx_book} {_ctx_chapter}:{candidate}"
                            logger.info(f"🔍 SEQUENTIAL: {ref} ({int(confidence*100)}% Acc)")
                            deliver_verse(ref, controller, bypass_cooldown=False, confidence=confidence, source="SEQUENTIAL")
                            trigger_onwards_if_needed(ref, text)
                            return True
                except ValueError:
                    pass

        # Layer 5b — "read-intent" range/single verse without explicit verse keyword.
        # Catches "let's read four and five", "read from verse four", "reading three and four"
        # when we have chapter context but no current verse yet.
        # This fires BEFORE Layer 6 so the strict "no current_verse" guard there doesn't block it.
        _READ_INTENT_RE = re.compile(
            r"\b(?:read|reading|let\s*['\u2019]?s\s+read|we\s+read|let\s+us\s+read|from)\b",
            re.IGNORECASE,
        )
        if current_book and current_chapter and not current_verse:
            if _READ_INTENT_RE.search(text):
                num_norm_ri = normalize_numbers_only(text)
                # Multi-verse: "read four and five" / "read three to seven"
                range_ri = RANGE_RE.search(num_norm_ri)
                if range_ri:
                    start_ri = int(range_ri.group("start"))
                    end_ri   = int(range_ri.group("end"))
                    if 1 <= start_ri < end_ri <= start_ri + 30:
                        ref_start = f"{current_book} {current_chapter}:{start_ri}"
                        logger.info(
                            f"🔍 READ-INTENT RANGE: {current_book} {current_chapter}:{start_ri}→{end_ri} "
                            f"({int(confidence*100)}% Acc)"
                        )
                        deliver_verse(ref_start, controller, bypass_cooldown=False,
                                      confidence=confidence, source="READ-INTENT-RANGE")
                        queue_verse_range(current_book, current_chapter, start_ri, end_ri, controller)
                        trigger_onwards_if_needed(ref_start, text)
                        return True
                # Single verse: "let's read verse four" / "read from four"
                m_single_ri = re.search(r'\b(\d{1,3})\b', num_norm_ri)
                if m_single_ri:
                    candidate_ri = m_single_ri.group(1)
                    ref_ri = f"{current_book} {current_chapter}:{candidate_ri}"
                    logger.info(
                        f"🔍 READ-INTENT: {ref_ri} ({int(confidence*100)}% Acc)"
                    )
                    deliver_verse(ref_ri, controller, bypass_cooldown=False,
                                  confidence=confidence, source="READ-INTENT")
                    trigger_onwards_if_needed(ref_ri, text)
                    return True

        # Layer 6 — range without explicit verse
        if current_book and current_chapter:
            range_m = RANGE_RE.search(num_norm)
            if range_m:
                start_v    = int(range_m.group("start"))
                end_v      = int(range_m.group("end"))
                text_after = num_norm[range_m.end():].strip()
                blockers   = [
                    "bibles", "dollars", "days", "weeks", "months", "years",
                    "minutes", "hours", "times", "people", "men", "women",
                    "students", "countries", "churches", "teams",
                ]
                # If we only have chapter context (no current_verse), be very strict.
                # "seven to twelve" when we just said "Daniel 1" is almost certainly chapters.
                # Only accept as verse range if "verse" or "v" is in the text near the range.
                is_explicit_v = bool(re.search(r'\b(?:verse|verses|v|vs)\b', num_norm.lower()))
                
                if not any(text_after.startswith(b) for b in blockers):
                    # If no verse is active, require "verse" keyword to avoid chapter-range confusion
                    if not current_verse and not is_explicit_v:
                        return False

                    if 1 <= start_v < end_v <= start_v + 30:
                        ref_start = f"{current_book} {current_chapter}:{start_v}"
                        logger.info(
                            f"🔍 RANGE: {current_book} {current_chapter}:{start_v}→{end_v} "
                            f"({int(confidence*100)}% Acc)"
                        )
                        deliver_verse(ref_start, controller, bypass_cooldown=False, confidence=confidence, source="RANGE")
                        queue_verse_range(current_book, current_chapter, start_v, end_v, controller)
                        trigger_onwards_if_needed(ref_start, text)
                        return True

        # Layer 8 — simple "Book chapter" pattern
        # Bug 3: require an explicit reference cue so casual words like "acts" don't fire
        m_simple = re.search(
            r'\b((?:[1-3]\s*)?(?:' + '|'.join(BOOK_KEYWORDS[:40]) + r'))\s+(\d{1,3})\b',
            text, re.IGNORECASE,
        )
        if m_simple:
            # Require that the match is preceded by a reference cue OR the raw text has a colon/digit
            pre_text   = text[:m_simple.start()].lower()
            post_digit = m_simple.group(2)  # the chapter number
            has_ref_cue = bool(re.search(
                r'\b(?:book of|chapter|chap|ch|turn to|open to|read|verse)\s*$', pre_text.strip()
            ))
            # Also accept if a digit directly follows (e.g. "Acts 13:2" has ":" in raw text)
            has_colon_verse = bool(re.search(
                rf'{re.escape(post_digit)}\s*[:v]\s*\d', text[m_simple.start():m_simple.end()+5], re.IGNORECASE
            ))
            if not has_ref_cue and not has_colon_verse:
                logger.debug(
                    f"🚫 BLOCKED Layer 8 False Positive (no ref cue): "
                    f"{m_simple.group(1).strip()} {post_digit}"
                )
            else:
                ref = f"{m_simple.group(1).strip().title()} {post_digit}"
                logger.info(f"🔍 SIMPLE: {ref} ({int(confidence*100)}% Acc)")
                deliver_verse(ref, controller, bypass_cooldown=False, confidence=confidence)
                trigger_onwards_if_needed(ref, text)
                return True

        # Layer 9 — LLM fallback (Groq only)
        if not LLM_ENABLED:
            return False

        text_lower = text.lower()
        has_book   = any(kw in text_lower for kw in BOOK_KEYWORDS)
        has_number = bool(re.search(r'\d+', text)) or any(w in text_lower for w in NUMBER_WORDS)

        # Issue 4 fix: long verse-like text with active context gets one LLM attempt
        # even if it has no book keyword or number (e.g. "meditation of my heart be accepted").
        _is_verse_quote_candidate = (
            len(text.split()) >= 8
            and current_book
            and current_chapter
            and (time.time() - _last_explicit_ref_time) < _EXPLICIT_REF_EXPIRY
        )

        if not has_book and not has_number and not _is_verse_quote_candidate:
            return False
        # Require BOTH a book name AND a number before burning an LLM call
        # (unless this is a verse-quote candidate)
        if not (has_book and has_number) and not _is_verse_quote_candidate:
            return False

        # Need at least 6 words so context is rich enough for LLM
        if len(text.split()) < 6:
            return False

        # ── Paraphrase-content guard ──────────────────────────────────────────
        # If the active anchor is set and the text contains known verse-content
        # phrases (especially for a recently-displayed verse), skip LLM entirely.
        # This prevents the LLM from reverse-engineering a reference from
        # exposition text that merely resembles the verse being preached.
        _PARAPHRASE_PHRASES = [
            # Acts 1:8 family
            "you will be my witnesses", "you shall be my witnesses",
            "to the ends of the earth", "unto the uttermost part of the earth",
            "receive power when the holy spirit",
            # Common exposition patterns
            "jesus said", "the lord said", "god said",
            "in the beginning", "thus saith the lord",
        ]
        if current_book and current_chapter:
            text_lower_guard = text.lower()
            for phrase in _PARAPHRASE_PHRASES:
                if phrase in text_lower_guard:
                    # Only skip if there's NO explicit reference signal in the text
                    has_explicit = bool(
                        re.search(r'[A-Za-z]\w*\s+\d{1,3}:\d{1,3}', text)
                        or re.search(r'(?:chapter|chap|ch)\s+\d{1,3}\s+(?:verse|v)\s+\d{1,3}', text, re.IGNORECASE)
                    )
                    if not has_explicit:
                        logger.debug(
                            f"🤖 LLM call BLOCKED (paraphrase-content guard): "
                            f"matched phrase '{phrase}' — no explicit ref signal in text"
                        )
                        return False
                    break  # explicit signal found, allow LLM to proceed

        global _llm_in_flight
        if _llm_in_flight:
            return False  # let partial_context keep growing instead

        # Bug 5: Deduplication via MD5 hash + minimum transcript advancement threshold
        import hashlib as _hashlib
        global _llm_last_key, _llm_last_time, _llm_last_dispatch_len
        llm_hash = _hashlib.md5(text_lower.encode()).hexdigest()
        now_ts   = time.time()
        if _llm_last_key == llm_hash:
            logger.warning(f"⚠️ Duplicate LLM call suppressed (same context hash): '{text[:60]}...'")
            return False
        # Require at least 30 new characters in the running transcript since last dispatch
        chars_added = len(full_sermon_transcript) - _llm_last_dispatch_len
        if chars_added < 30 and _llm_last_key is not None:
            logger.debug(f"LLM call skipped: only {chars_added} new chars since last dispatch (need 30)")
            return False
        if (now_ts - _llm_last_time) < 25:
            return False
        # Bug 3: Thematic-only hits (no book keyword in raw text) require a recent explicit ref
        if not has_book and (now_ts - _last_explicit_ref_time) > _EXPLICIT_REF_EXPIRY:
            logger.debug(f"LLM thematic hit suppressed: no explicit ref in last {int(_EXPLICIT_REF_EXPIRY)}s")
            return False
        _llm_last_key          = llm_hash
        _llm_last_time         = now_ts
        _llm_last_dispatch_len = len(full_sermon_transcript)

        logger.info(f"📞 LLM: '{text[:80]}'")
        _llm_in_flight = True

        def llm_task():
            global _llm_in_flight, _last_explicit_ref_time
            try:
                verse = extract_verse_with_llm(text)
                if verse:
                    # Bug 5 fix (refined): Suppress LLM verses that are genuinely stale —
                    # i.e. the sermon has moved well past them AND they are not a valid
                    # backreference within the *current* sermon passage.
                    #
                    # Original behaviour: suppress whenever high-water > detected verse.
                    # Problem: that incorrectly dropped valid same-sermon-chapter revisits
                    # (e.g. preacher at Daniel 12:12 re-emphasises Daniel 12:2).
                    #
                    # Refined rule:
                    #   SUPPRESS  — high-water is ahead AND the detected book+chapter does
                    #               NOT match the active sermon anchor (i.e. it is from an
                    #               older/unrelated passage, not the current one).
                    #   ACCEPT    — same book+chapter as the sermon anchor (backreference or
                    #               repeated emphasis within the active passage is intentional).
                    _suppress_stale_llm = False
                    if ":" in verse:
                        try:
                            _llm_parts   = verse.rsplit(":", 1)
                            _llm_book_ch = _llm_parts[0].strip()   # e.g. "Daniel 12"
                            _llm_v_num   = int(_llm_parts[1].split()[0])
                            _hw_key      = _llm_book_ch             # same key as _session_verse_high_water
                            _hw_verse    = _session_verse_high_water.get(_hw_key, 0)

                            # Active sermon anchor key, e.g. "Daniel 12"
                            _sa_key = (
                                f"{_sermon_anchor_book} {_sermon_anchor_chapter}"
                                if _sermon_anchor_book and _sermon_anchor_chapter
                                else None
                            )
                            _is_same_sermon_passage = (
                                _sa_key is not None
                                and _llm_book_ch.lower() == _sa_key.lower()
                            )

                            if _hw_verse > _llm_v_num:
                                if _is_same_sermon_passage:
                                    # Backreference within the active sermon chapter — the
                                    # preacher is revisiting or re-emphasising an earlier verse.
                                    # Accept it; do NOT set _suppress_stale_llm.
                                    logger.info(
                                        f"✅ LLM stale-check BYPASSED (same sermon passage): {verse} "
                                        f"| active_sermon={_sa_key} "
                                        f"| hw={_hw_verse} | extracted_v={_llm_v_num} "
                                        f"| decision=ACCEPTED "
                                        f"| reason=same-chapter backreference within active passage"
                                    )
                                else:
                                    # Genuinely stale: belongs to an earlier / unrelated section.
                                    logger.info(
                                        f"🔕 LLM result suppressed (stale): {verse} "
                                        f"| active_sermon={_sa_key or 'none'} "
                                        f"| hw={_hw_verse} | extracted_v={_llm_v_num} "
                                        f"| decision=SUPPRESSED "
                                        f"| reason=sermon has moved past this verse in a different passage"
                                    )
                                    _suppress_stale_llm = True
                            else:
                                logger.debug(
                                    f"✅ LLM stale-check passed (verse not behind hw): {verse} "
                                    f"| active_sermon={_sa_key or 'none'} "
                                    f"| hw={_hw_verse} | extracted_v={_llm_v_num} "
                                    f"| decision=ACCEPTED"
                                )
                        except (ValueError, IndexError, AttributeError):
                            pass
                    if not _suppress_stale_llm:
                        _last_explicit_ref_time = time.time()
                        deliver_verse(verse, controller, bypass_cooldown=False, confidence=confidence, source="LLM")
                        trigger_onwards_if_needed(verse, text)
                        check_and_queue_range(text, verse, controller)
            finally:
                _llm_in_flight = False

        threading.Thread(target=llm_task, daemon=True).start()
        # Return False — partial_context keeps accumulating until a verse is confirmed
        return False


    except Exception as e:
        logger.error(f"Parse error: {e}")
        return False


# ── SENTENCE SPLITTER ─────────────────────────────────────────────────────────
_CLAUSE_SPLIT_RE = re.compile(r'(?<=[.!?।])\s+') 


def _is_explicit_full_ref(text: str) -> bool:
    """Return True when *text* contains a fully explicit book + chapter + verse
    reference that should bypass the contextual floor.

    Accepts all of:
      • Colon notation          — "Daniel 11:5", "Acts 9:15"
      • Spoken chapter+verse    — "Daniel chapter 11 verse 5"
      • Numbered-book variants  — "1 Corinthians 13:4", "2 Kings chapter 2 verse 11"

    Does NOT match bare "verse 5" or bare chapter-only refs like "Daniel 11"
    because those are inferred / contextual and the floor should still apply.
    """
    # Fast path: colon notation with a word before it (book name present)
    if re.search(r'[A-Za-z]\w*\s+\d{1,3}:\d{1,3}', text):
        return True
    # Spoken form: book ... chapter N ... verse N
    if re.search(
        r'[A-Za-z]\w*\s+(?:chapter|chap|ch)\s+\d{1,3}\s+(?:verse|v)\s+\d{1,3}',
        text, re.IGNORECASE
    ):
        return True
    # Numbered-book colon form: "1 Kings 2:3"
    if re.search(r'[1-3]\s+[A-Za-z]\w*\s+\d{1,3}:\d{1,3}', text):
        return True
    # Numbered-book spoken form: "1 Kings chapter 2 verse 3"
    if re.search(
        r'[1-3]\s+[A-Za-z]\w*\s+(?:chapter|chap|ch)\s+\d{1,3}\s+(?:verse|v)\s+\d{1,3}',
        text, re.IGNORECASE
    ):
        return True
    return False


def _detect_explicit_reference(sentence: str, controller) -> bool:
    """Bug 7: Fast-path for fully explicit references (book + chapter + verse).
    Runs the parser directly on the raw sentence and delivers immediately,
    bypassing the LLM window queue. Only fires when chapter AND verse are present."""
    # Bug Fix 2B: strip ordinal-occasion phrases before parsing
    clean = _strip_ordinal_occasions(sentence)
    refs = PRIMARY_PARSER(clean)
    if not refs:
        return False
    for ref in refs:
        if ":" in ref:  # must have chapter:verse — not just a chapter
            parts = ref.rsplit(":", 1)
            chap  = parts[0].split()[-1]
            verse = parts[1]
            if _is_range_not_verse(sentence, chap, verse):
                logger.debug(f"⚡ FAST-PATH skipped: '{ref}' looks like chapter range in '{sentence[:60]}'")
                continue
            if _is_book_count_number(sentence, chap):
                logger.debug(f"⚡ FAST-PATH skipped: '{ref}' chapter is a book-count in '{sentence[:60]}'")
                continue
            # Unified ambiguous-book-as-person guard (replaces John-only checks).
            # Covers John, Matthew, Mark, Luke, James, Ruth, Joel, Job, Amos, Jonah,
            # Micah, Peter, Jude, Hosea, Nahum, Philemon, Timothy, Titus.
            _fp_ref_book      = " ".join(ref.split()[:-1])
            _fp_book_last     = _fp_ref_book.split()[-1] if _fp_ref_book else ""
            if _is_book_as_person(_fp_book_last, sentence):
                logger.debug(
                    f"⚡ FAST-PATH skipped: '{_fp_book_last}' is a person/topic name"
                    f" in '{sentence[:60]}'"
                )
                continue
            # Structural-impossibility check — no substitution; drop entirely.
            if _is_structurally_impossible(ref, sentence):
                logger.debug(f"⚡ FAST-PATH skipped: '{ref}' is structurally impossible")
                continue
            if _reject_verse_out_of_range(ref):
                continue

            # Bug 1 fix: Narrative-reading guard — if the sentence describes someone
            # ELSE reading a passage (e.g. "he was reading Isaiah 53"), do NOT treat
            # this as the preacher announcing a new passage.  The detected ref would
            # silently switch context so that all subsequent bare-verse numbers map to
            # the narrative book (the Isaiah 53 / Acts 8 contamination bug).
            ref_book = " ".join(ref.split()[:-1])   # everything before "chapter:verse"
            if current_book and ref_book.lower() != current_book.lower():
                if _is_narrative_reading_context(sentence, ref_book):
                    logger.info(f"⚡ FAST-PATH skipped: narrative reading context for '{ref}' (active context: {current_book} {current_chapter})")
                    continue

            logger.info(f"⚡ FAST-PATH explicit ref: {ref}")
            deliver_verse(ref, controller, bypass_cooldown=True, confidence=1.0, source="FAST-PATH")
            trigger_onwards_if_needed_standalone(ref, sentence)
            return True

    # Bug EN-3 fix: catch "chapter N ... [verse] X and Y" patterns where the parser
    # either missed it or only returned a chapter-only ref.
    # Example: "Second Corinthians chapter ten... let's read four and five"
    # The parser returns "2 Corinthians 10" (no verse). We extract the first verse
    # from "X and Y" using current context, then queue the second.
    if current_book and current_chapter:
        m_and = re.search(r'\b(?:verse[s]?\s+)?(\d+)\s+and\s+(\d+)\b', clean, re.IGNORECASE)
        if m_and:
            first_v  = m_and.group(1)
            second_v = m_and.group(2)
            ref_first = f"{current_book} {current_chapter}:{first_v}"
            if not _reject_verse_out_of_range(ref_first):
                logger.info(f"⚡ FAST-PATH (X-and-Y): {ref_first} (plus v{second_v} queued)")
                deliver_verse(ref_first, controller, bypass_cooldown=True, confidence=1.0, source="FAST-PATH")
                trigger_onwards_if_needed_standalone(ref_first, sentence)
                # Queue the second verse so it auto-advances
                ref_second = f"{current_book} {current_chapter}:{second_v}"
                if not _reject_verse_out_of_range(ref_second):
                    check_and_queue_range(clean, ref_second, controller)
                return True

        # Issue 2 fix: "Book chapter N V" — parser returns chapter-only ref but a bare
        # verse number follows immediately (e.g. "Acts chapter one eight" → Acts 1:8).
        # Look for a second standalone digit right after the chapter number in num_norm.
        _clean_norm = normalize_numbers_only(clean)
        _chap_v_m = re.search(
            r'\b(?:chapter|chap|ch)\s+(\d{1,3})\s+(\d{1,3})\b',
            _clean_norm, re.IGNORECASE,
        )
        if _chap_v_m:
            chap_n  = _chap_v_m.group(1)
            verse_n = _chap_v_m.group(2)
            # Only fire if the chapter matches current context (or no chapter yet set)
            if not current_chapter or current_chapter == chap_n:
                ref_cv = f"{current_book} {chap_n}:{verse_n}"
                if not _reject_verse_out_of_range(ref_cv):
                    logger.info(f"⚡ FAST-PATH (chap-verse-adjacent): {ref_cv}")
                    deliver_verse(ref_cv, controller, bypass_cooldown=True, confidence=1.0, source="FAST-PATH")
                    trigger_onwards_if_needed_standalone(ref_cv, sentence)
                    return True

    return False


def trigger_onwards_if_needed_standalone(ref_string: str, original_text: str):
    """Standalone version of trigger_onwards_if_needed for fast-path use (no closure over detect_verse_hybrid)."""
    if any(kw in original_text.lower() for kw in ONWARDS_KEYWORDS):
        parts = ref_string.split()
        if ":" in parts[-1]:
            ch, vs = parts[-1].split(":")
            bk     = " ".join(parts[:-1])
            if current_book and current_chapter:
                if bk != current_book or ch != current_chapter:
                    bk = current_book
                    ch = current_chapter
            _start_onwards(bk, ch, vs)


def _detect_from_translation(english_text: str, controller) -> bool:
    """Bug 1 Fix: When Sarvam auto-translates Malayalam → English it may produce
    colon-notation references (e.g. "John 12:27", "Matthew 3:5") that are not
    present in the raw Malayalam blob.  This helper runs parse_eng on the
    translated text and delivers ONLY high-confidence chapter:verse hits
    (colon required) to avoid false positives from hallucinated book names.
    It is called in addition to — not instead of — the Malayalam processing.
    """
    if not english_text or not english_text.strip():
        return False
    if not USE_SARVAM:
        return False
    try:
        refs = parse_eng(english_text)
    except Exception:
        return False
    for ref in refs:
        if ":" not in ref:
            continue  # chapter-only guesses from translated text are too risky
        # Require the translated text to be substantial enough to be reliable.
        # Very short translations (e.g. hallucinated "Joel 3:5") are discarded.
        if len(english_text.split()) < 5:
            continue
        if _is_book_count_number(english_text, ref.split()[-1].split(":")[0]):
            continue
        if _reject_verse_out_of_range(ref):
            continue
        # Unified ambiguous-book-as-person guard — same logic as FAST-PATH.
        _tr_ref_book  = " ".join(ref.split()[:-1])
        _tr_book_last = _tr_ref_book.split()[-1] if _tr_ref_book else ""
        if _is_book_as_person(_tr_book_last, english_text):
            logger.debug(
                f"⚡ TRANSLATION-PATH skipped: '{_tr_book_last}' is a person/topic"
                f" name in translated text '{english_text[:60]}'"
            )
            continue
        # Structural-impossibility check — no substitution; drop the ref entirely.
        if _is_structurally_impossible(ref, english_text):
            logger.debug(f"⚡ TRANSLATION-PATH skipped: '{ref}' is structurally impossible")
            continue
        logger.info(f"⚡ TRANSLATION-PATH ref: {ref}")
        deliver_verse(ref, controller, bypass_cooldown=True, confidence=1.0, source="TRANSLATION-PATH")
        trigger_onwards_if_needed_standalone(ref, english_text)
        return True
    return False


def _process_transcript_blob(sentence: str, partial_context_ref: list, controller, parser=None):
    # NOTE: WORSHIP_MODE does NOT bail here — detection runs fully for debug logging.
    # The display gate is inside send_verse / VerseController.send_verse.

    # ── SCRIPTURE-READ: check entry/exit triggers on every sentence ──────────
    # Runs before any detection so the mode flag is correct for all downstream
    # filtering.  Entry phrases like "open your Bibles" or "let's read" flip the
    # flag on; exit phrases (topic shift, new anchor in a different book) flip it
    # off.  This does NOT short-circuit the detection pipeline — WORSHIP_MODE
    # semantics apply here too: the run completes, the gate decides what shows.
    _scripture_read_check_entry_exit(sentence)

    # ── SCRIPTURE-READ: scrub stray numerals from the sentence ────────────────
    # Timestamps, sermon point numbers, statistics, year references and similar
    # noise are stripped so the detection layers never see them as verse numbers
    # while the mode is active.
    sentence = _scripture_read_filter(sentence)

    # Bug 5: Self-correction detector — if the speaker says 'sorry' / 'I mean' / 'I meant',
    # discard the text before the correction and only parse what follows it.
    _corr_m = _CORRECTION_RE.search(sentence)
    if _corr_m:
        corrected = sentence[_corr_m.end():].strip()
        if corrected:
            logger.debug(f"🔄 Self-correction detected — using: '{corrected}'")
            sentence = corrected

    partial_context = partial_context_ref[0]

    # Bug 7: Explicit full reference fast-path — fires before partial context even accumulates
    if _detect_explicit_reference(sentence, controller):
        partial_context_ref[0] = ""  # clear context after an explicit hit
        return

    parts = _CLAUSE_SPLIT_RE.split(sentence.strip())
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if check_smart_amen(part, controller):
            partial_context = ""
            break
        check_verse_queue(part, controller)
        partial_context += " " + part
        # Ambiguity penalty: very short blobs (≤3 words) are high-ambiguity fragments.
        # Reduce confidence so the contextual / sequential layers can't fire from a
        # 2-word burst alone — they need a stronger signal.
        _blob_words    = len(partial_context.split())
        _blob_conf     = 1.0 if _blob_words > 3 else 0.75
        found = detect_verse_hybrid(partial_context.strip(), controller, confidence=_blob_conf, parser=parser)
        if found:
            partial_context = ""
            break
    if partial_context:
        words = partial_context.split()
        if len(words) > 50:
            partial_context = " ".join(words[-25:])
    partial_context_ref[0] = partial_context


# ── DEEPGRAM STREAMING ────────────────────────────────────────────────────────
async def stream_audio(controller, is_secondary=False):
    global full_sermon_transcript, full_sermon_transcript_secondary
    import websockets
    import json

    # Resolve which config to use based on primary vs secondary
    if is_secondary:
        _lang    = SECONDARY_DEEPGRAM_LANGUAGE
        _model   = SECONDARY_DEEPGRAM_MODEL
        _parser  = SECONDARY_PARSER
        _tag     = "[SEC]"
    else:
        _lang    = DEEPGRAM_LANGUAGE
        _model   = DEEPGRAM_MODEL
        _parser  = None   # None → detect_verse_hybrid uses PRIMARY_PARSER
        _tag     = "[PRI]"

    partial_context = [""]

    import pyaudio
    audio  = pyaudio.PyAudio()
    stream = None

    try:
        mic_info = audio.get_device_info_by_index(MIC_INDEX)
        logger.info(f"Using: [{MIC_INDEX}] {mic_info['name']}")
        if "stereo mix" in mic_info['name'].lower():
            logger.warning("⚠️ Stereo Mix selected — ALL desktop audio will be captured. Non-church audio may trigger false detections.")
        stream = audio.open(
            format=pyaudio.paInt16, channels=1, rate=RATE,
            input=True, input_device_index=MIC_INDEX,
            frames_per_buffer=CHUNK,
        )
        logger.info("Microphone opened")
    except Exception as e:
        logger.error(f"Microphone error: {e}")
        return

    # ── Deepgram keywords boosting — helps Nova-3 Hindi recognise accented
    # English Bible book names (e.g. "Corintens" → "Corinthians") ──────────
    _BIBLE_KEYWORDS = [
        "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy",
        "Joshua", "Judges", "Ruth", "Samuel", "Kings", "Chronicles",
        "Ezra", "Nehemiah", "Esther", "Job", "Psalms", "Proverbs",
        "Ecclesiastes", "Isaiah", "Jeremiah", "Lamentations", "Ezekiel",
        "Daniel", "Hosea", "Joel", "Amos", "Obadiah", "Jonah", "Micah",
        "Nahum", "Habakkuk", "Zephaniah", "Haggai", "Zechariah", "Malachi",
        "Matthew", "Mark", "Luke", "John", "Acts", "Romans",
        "Corinthians", "Galatians", "Ephesians", "Philippians", "Colossians",
        "Thessalonians", "Timothy", "Titus", "Philemon", "Hebrews",
        "James", "Peter", "Jude", "Revelation",
    ]
    _kw_params = "".join(
        f"&keyterm={kw}" for kw in _BIBLE_KEYWORDS
    ) if _lang == "hi" else ""

    url = (
        f"wss://api.deepgram.com/v1/listen"
        f"?language={_lang}"
        f"&model={_model}"
        f"&punctuate=true"
        f"&smart_format=false"
        f"&interim_results=true"
        f"&utterance_end_ms=1000"
        f"&endpointing=300"
        f"&encoding=linear16"
        f"&sample_rate={RATE}"
        f"{_kw_params}"
    )
    headers = {"Authorization": f"Token {DEEPGRAM_API_KEY}"}
    loop    = asyncio.get_event_loop()

    def read_audio():
        return stream.read(CHUNK, exception_on_overflow=False)

    try:
        async with websockets.connect(url, additional_headers=headers) as ws:
            logger.info(f"🎤 {_tag} Language: {_lang.upper()} | Model: {_model.upper()}")
            logger.info(f"Connected to Deepgram WebSocket {_tag}")
            logger.info("Press Stop to end")

            async def recv_transcripts():
                global full_sermon_transcript, full_sermon_transcript_secondary, _last_transcript_time
                try:
                    async for msg in ws:
                        try:
                            data     = json.loads(msg)
                            msg_type = data.get("type", "Results")
                            if msg_type != "Results":
                                continue
                            channel = data.get("channel", {})
                            if isinstance(channel, list):
                                continue
                            alts = channel.get("alternatives", [])
                            if not alts or not isinstance(alts[0], dict):
                                continue
                            sentence = alts[0].get("transcript", "")
                            if not sentence.strip():
                                continue
                            check_verse_queue(sentence, controller)
                            if data.get("is_final"):
                                # Bug 3: Detect and collapse repeated phrases
                                global _last_sentence
                                collapsed = False
                                words = sentence.strip().split()
                                # Check for phrases repeated more than 3 times consecutively
                                for i in range(len(words) - 6):
                                    phrase = " ".join(words[i:i+3])
                                    repeat_count = 1
                                    j = i + 3
                                    while j <= len(words) - 3:
                                        next_phrase = " ".join(words[j:j+3])
                                        if next_phrase == phrase:
                                            repeat_count += 1
                                            j += 3
                                        else:
                                            break
                                    if repeat_count > 3:
                                        logger.info(f"📝 {_tag} {phrase}... (repeated {repeat_count}x, collapsed)")
                                        logger.warning(f"⚠️ Transcript repetition detected and collapsed")
                                        sentence = phrase + "..."
                                        collapsed = True
                                        break

                                # Issue B: secondary-stream degenerate-loop guard.
                                # After the existing phrase-collapse above, run the
                                # heavier token-loop detector.  If the chunk is still
                                # degenerate after collapsing, drop it entirely rather
                                # than feeding garbage into the verse pipeline.
                                if is_secondary and _drop_if_degenerate(sentence, _tag):
                                    continue   # chunk dropped — do not append or parse

                                if not collapsed:
                                    logger.info(f"📝 {_tag} {sentence}")

                                # Append to the appropriate transcript buffer
                                full_sermon_transcript += " " + sentence.strip()
                                if is_secondary:
                                    full_sermon_transcript_secondary += " " + sentence.strip()
                                _last_transcript_time = time.time()  # Feature 6
                                _process_transcript_blob(sentence, partial_context, controller, parser=_parser)
                        except Exception as e:
                            logger.error(f"Recv error {_tag}: {e}")
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.warning(f"WebSocket closed {_tag}: {e}")

            async def send_audio():
                # Issue B: catch websocket send errors gracefully.  A
                # ConnectionClosed / SendError from the secondary stream used to
                # bubble up and trigger a full shutdown.  Now we log it and let
                # the outer reconnect loop handle recovery.
                try:
                    while not stop_event.is_set():
                        data = await loop.run_in_executor(None, read_audio)
                        try:
                            await ws.send(data)
                        except Exception as _send_exc:
                            _exc_name = type(_send_exc).__name__
                            if is_secondary:
                                logger.warning(
                                    f"⚠️ {_tag} websocket send error ({_exc_name}) — "
                                    f"graceful fallback: stopping sender, "
                                    f"reconnect will be attempted by outer loop"
                                )
                            else:
                                logger.error(f"Send error: {_send_exc}")
                            break   # exit sender; receiver/outer loop handle reconnect
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.error(f"Send error: {e}")

            sender   = asyncio.create_task(send_audio())
            receiver = asyncio.create_task(recv_transcripts())
            await stop_event.wait()
            sender.cancel()
            receiver.cancel()
            await asyncio.gather(sender, receiver, return_exceptions=True)
            try:
                await ws.send(json.dumps({"type": "CloseStream"}))  # type: ignore
            except Exception:
                pass
    except Exception as e:
        err_str = str(e)
        if "401" in err_str:
            logger.error("❌ Deepgram API key rejected (HTTP 401). Check your key in Advanced Settings.")
        else:
            logger.error(f"Deepgram WebSocket error: {e}")
    finally:
        # On macOS/Intel the CoreAudio callback runs in a separate PortAudio thread.
        # Calling stop_stream() while run_in_executor(read_audio) is still in-flight
        # causes a SIGSEGV (zsh: segmentation fault). Fix:
        #   1. Wait one CHUNK period so the in-flight blocking read() can return.
        #   2. Use abort_stream() on macOS — it kills the stream immediately without
        #      waiting to drain the buffer, which prevents the re-entrancy crash.
        #   3. Sleep between each PortAudio call to let the OS callback thread settle.
        import time as _pa_t
        _chunk_secs = CHUNK / max(RATE, 1)
        _pa_t.sleep(_chunk_secs + 0.05)   # let in-flight executor read() return
        if stream:
            try:
                if sys.platform == "darwin":
                    stream.abort_stream()   # immediate — no drain wait
                else:
                    stream.stop_stream()
            except Exception:
                pass
            _pa_t.sleep(0.05)
            try:
                stream.close()
            except Exception:
                pass
        _pa_t.sleep(0.1)  # give PortAudio callback thread time to exit
        try:
            audio.terminate()
        except Exception:
            pass


# ── Issue B: repetition / noise guard ────────────────────────────────────────

def _is_degenerate_chunk(text: str) -> tuple[bool, str]:
    """Return (True, reason) when *text* looks like a degenerate token-loop.

    Checks two patterns:
      1. Single-token or two-token loops repeated >= _REP_MIN_TOKEN_LOOP times.
         e.g. "I I I I I I" (6× "I") or "go to go to go to go to" (4× "go to")
      2. Three-token phrase loops repeated >= _REP_MIN_PHRASE_LOOP times.
         e.g. "and he said and he said and he said and he said"

    Normal speech with incidental repetition (stutters, emphasis) will not trigger
    because the thresholds are intentionally high.
    """
    words = text.strip().split()
    if len(words) < _REP_MIN_TOKEN_LOOP:
        return False, ""

    # ── 1-token loop ──────────────────────────────────────────────────────────
    if len(set(words)) == 1:
        if len(words) >= _REP_MIN_TOKEN_LOOP:
            return True, f"single-token loop '{words[0]}' ×{len(words)}"

    # ── 2-token and 3-token phrase loops ─────────────────────────────────────
    for phrase_len, threshold in ((2, _REP_MIN_TOKEN_LOOP), (3, _REP_MIN_PHRASE_LOOP)):
        if len(words) < phrase_len * threshold:
            continue
        for start in range(phrase_len):
            chunks = [
                " ".join(words[i : i + phrase_len])
                for i in range(start, len(words) - phrase_len + 1, phrase_len)
            ]
            if not chunks:
                continue
            # All chunks identical → pure loop
            if len(set(chunks)) == 1 and len(chunks) >= threshold:
                return True, f"{phrase_len}-token loop '{chunks[0]}' ×{len(chunks)}"

    return False, ""


def _drop_if_degenerate(text: str, tag: str) -> bool:
    """Return True (and log) if *text* is degenerate and should be dropped.

    Also enforces a per-tag throttle window: if a drop was just triggered,
    the next _REP_DROP_WINDOW_SEC of chunks from the same tag are dropped too,
    giving the STT model time to recover before we resume processing.
    """
    now = time.time()

    # Still inside the throttle window from a previous drop?
    if now < _rep_drop_until.get(tag, 0.0):
        logger.debug(
            f"🔇 {tag} chunk dropped (throttle window active, "
            f"{_rep_drop_until[tag] - now:.1f}s remaining): '{text[:60]}'"
        )
        return True

    degenerate, reason = _is_degenerate_chunk(text)
    if degenerate:
        logger.warning(
            f"♻️ {tag} repetition detected — chunk dropped | "
            f"reason={reason} | text='{text[:80]}'"
        )
        _rep_drop_until[tag] = now + _REP_DROP_WINDOW_SEC
        logger.info(
            f"⏳ {tag} throttle window active for {_REP_DROP_WINDOW_SEC:.0f}s "
            f"(allowing STT model to recover)"
        )
        return True

    return False


# ── SARVAM STREAMING ──────────────────────────────────────────────────────────
async def stream_audio_sarvam(controller, is_secondary=False):
    global full_sermon_transcript, full_sermon_transcript_secondary
    import base64
    from sarvamai import AsyncSarvamAI
    import pyaudio

    _parser = SECONDARY_PARSER if is_secondary else None
    _tag    = "[SEC-ML]" if is_secondary else "[PRI-ML]"

    audio  = pyaudio.PyAudio()
    stream = None

    try:
        mic_info = audio.get_device_info_by_index(MIC_INDEX)
        logger.info(f"Using: [{MIC_INDEX}] {mic_info['name']}")
        stream = audio.open(
            format=pyaudio.paInt16, channels=1, rate=RATE,
            input=True, input_device_index=MIC_INDEX, frames_per_buffer=CHUNK,
        )
        logger.info("Microphone opened")
    except Exception as e:
        logger.error(f"Microphone error: {e}")
        return

    def read_chunk_blocking():
        frames = []
        for _ in range(max(1, int(RATE * 0.5 / CHUNK))):
            frames.append(stream.read(CHUNK, exception_on_overflow=False))
        return b"".join(frames)

    client = AsyncSarvamAI(api_subscription_key=SARVAM_API_KEY)
    loop   = asyncio.get_event_loop()

    try:
        while not stop_event.is_set():
            logger.info("Connecting to Sarvam AI...")
            try:
                async with client.speech_to_text_streaming.connect(
                    model="saaras:v3",
                    # [Q1] mode="transcribe" is correct for live church sermon transcription.
                    #      Sarvam V3's streaming WebSocket is inherently real-time (sub-150ms latency)
                    #      regardless of mode.  The `mode` param only controls OUTPUT FORMAT:
                    #        "transcribe"  → high-accuracy Malayalam text  ✅ (correct for sermons)
                    #        "translate"   → Malayalam speech → English text
                    #        "translit"    → Malayalam speech → Roman/Manglish script
                    #        "codemix"     → code-switched audio (e.g. Malayalam+English mixed)
                    #      There is NO "realtime" or "realtime_accurate" mode value in V3's core API;
                    #      those strings only appear in third-party wrappers (Bolna, Pipecat, etc.).
                    mode="translit" if MALAYALAM_TRANSLITERATION else "transcribe",
                    # [Q3] language_code="ml-IN" — V3 natively supports all 22 scheduled Indian
                    #      languages including Malayalam.  Accuracy on Malayalam (including
                    #      Malayalam-English code-mix) is significantly improved over V2:
                    #      V2 required explicit language hints; V3 was trained end-to-end on
                    #      native Indian language data.  No code change needed; "ml-IN" is optimal.
                    language_code=SARVAM_LANGUAGE, sample_rate=RATE,
                    # [Q2] high_vad_sensitivity=True is the correct choice for sermon audio.
                    #      Sarvam V3 docs recommend True for responsive speech detection; the
                    #      tradeoff is that ~0.5s of silence marks a segment boundary (vs ~1s when
                    #      False).  For a preacher who pauses between sentences this is fine:
                    #      0.5s is shorter than a natural breath pause, so sentences are segmented
                    #      cleanly without early cut-off.  Setting False would only help if the
                    #      audio has persistent background noise that triggers false endpoints.
                    high_vad_sensitivity=True, vad_signals=False,
                    input_audio_codec="pcm_s16le",
                ) as ws:
                    logger.info(
                        f"Sarvam AI connected — {SARVAM_LANGUAGE} saaras:v3 "
                        f"({'translit/Manglish' if MALAYALAM_TRANSLITERATION else 'transcribe/Malayalam'})"
                    )
                    global _sarvam_ignore_until
                    _sarvam_ignore_until = time.time() + 3.0
                    logger.info("⏳ Ignoring post-reconnect audio (3s cooldown)")

                    partial_context = [""]

                    async def send_audio():
                        try:
                            while not stop_event.is_set():  # type: ignore
                                pcm_data = await loop.run_in_executor(None, read_chunk_blocking)  # type: ignore
                                try:
                                    await ws.transcribe(audio=base64.b64encode(pcm_data).decode("utf-8"))  # type: ignore
                                except Exception as _send_exc:
                                    logger.warning(
                                        f"⚠️ {_tag} send error ({type(_send_exc).__name__}) — "
                                        f"stopping sender; reconnect attempted by outer loop"
                                    )
                                    break   # exit sender; reconnect loop handles recovery
                        except asyncio.CancelledError:
                            pass
                        except Exception as e:
                            logger.error(f"Sarvam send error: {e}")

                    async def keepalive():
                        try:
                            while not stop_event.is_set():  # type: ignore
                                # Wait up to 25 s for stop — this makes the task
                                # respond instantly to cancellation and to stop_event,
                                # unlike asyncio.sleep() whose internal Future can be
                                # left pending when the event loop tears down.
                                try:
                                    await asyncio.wait_for(
                                        stop_event.wait(),  # type: ignore
                                        timeout=25,
                                    )
                                    break  # stop_event fired — exit cleanly
                                except asyncio.TimeoutError:
                                    pass  # 25 s elapsed; fall through to send keepalive
                                if stop_event.is_set():  # type: ignore
                                    break
                                silence = b'\x00' * CHUNK * 2
                                await ws.transcribe(audio=base64.b64encode(silence).decode("utf-8"))  # type: ignore
                        except asyncio.CancelledError:
                            pass   # explicit cancel from shutdown — exit cleanly
                        except Exception:
                            pass

                    async def recv_transcripts():
                        global full_sermon_transcript, full_sermon_transcript_secondary, _last_transcript_time
                        try:
                            async for message in ws:
                                try:
                                    if isinstance(message, dict):
                                        sentence = message.get("transcript", message.get("text", ""))
                                    else:
                                        # Bug 7: Sarvam Python SDK returns SpeechToTextStreamingResponse objects.
                                        # The transcript may be in message.data.transcript or message.transcript.
                                        sentence = (
                                            getattr(message.data, "transcript", "")
                                            if hasattr(message, "data")
                                            else getattr(message, "transcript",
                                                         getattr(message, "text", ""))
                                        )
                                    
                                    sentence = str(sentence).strip()
                                    if not sentence or sentence == "None":
                                        continue

                                    # Bug Fix 4: discard garbage audio from reconnect boundary
                                    if time.time() < _sarvam_ignore_until:
                                        continue

                                    # Issue B: degenerate token-loop guard for SEC-ML stream.
                                    # Sarvam sometimes enters a hallucination loop ("I I I…",
                                    # "go to go to…") which precedes websocket collapse.
                                    # Drop the chunk early and throttle for a few seconds so
                                    # the model can recover without forcing a full shutdown.
                                    if _drop_if_degenerate(sentence, _tag):
                                        continue

                                    if MALAYALAM_TRANSLITERATION:
                                        # ── Translit mode: Sarvam outputs Roman/Manglish directly.
                                        # The text is Latin-script but the WORDS are still Malayalam
                                        # (e.g. "Yohannaan muunnu padhinaaru" = "John 3:16").
                                        # We must still translate to English so that:
                                        #   • check_verse_queue can track verse progression correctly
                                        #   • _detect_from_translation can catch colon-notation refs
                                        # We parse the original Manglish blob too (catches any English
                                        # book names the preacher said aloud in English).
                                        manglish_text = sentence
                                        english_text  = translate_to_english(manglish_text)
                                        display_text  = manglish_text
                                        logger.info(f"📝 {_tag} [Manglish] {display_text}")
                                        if english_text and english_text != manglish_text:
                                            logger.info(f"🔤 {_tag} [Manglish→EN] {english_text}")
                                        check_verse_queue(english_text, controller)
                                        full_sermon_transcript += " " + english_text.strip()
                                        if is_secondary:
                                            full_sermon_transcript_secondary += " " + english_text.strip()
                                        _last_transcript_time = time.time()
                                        # Parse original Manglish — catches English book names spoken directly
                                        _process_transcript_blob(manglish_text, partial_context, controller, parser=_parser)
                                        # Also run translation-path detection on the English translation
                                        _detect_from_translation(english_text, controller)
                                    else:
                                        # ── Transcribe mode: native Malayalam script (original behaviour).
                                        malayalam_text = sentence
                                        english_text = translate_to_english(sentence)
                                        display_text = malayalam_text if show_malayalam_raw else english_text
                                        
                                        logger.info(f"📝 {_tag} {display_text}")
                                        if show_malayalam_raw and english_text != malayalam_text:
                                            logger.info(f"🔤 {_tag} {english_text}")

                                        check_verse_queue(english_text, controller)
                                        full_sermon_transcript += " " + english_text.strip()
                                        if is_secondary:
                                            full_sermon_transcript_secondary += " " + english_text.strip()
                                        _last_transcript_time = time.time()
                                        # Bug Fix 3A: Parse the original transcript (which preserves
                                        # English book names the preacher actually said) rather than
                                        # Sarvam's English translation, which can hallucinate names
                                        # like "John the Baptist" from Malayalam context words.
                                        _process_transcript_blob(malayalam_text, partial_context, controller, parser=_parser)
                                        # Bug 1 Fix: Also detect colon-notation references that only
                                        # appear in the auto-translation (e.g. "Matthew 3:5", "John 12:27").
                                        # _detect_from_translation uses parse_eng and requires a colon
                                        # so false positives from hallucinated names are minimal.
                                        _detect_from_translation(english_text, controller)
                                        
                                except Exception as e:
                                    logger.error(f"Sarvam message processing error {_tag}: {e}")
                        except asyncio.CancelledError:
                            pass
                        except Exception as e:
                            if not stop_event.is_set():
                                logger.warning(f"Sarvam session ended {_tag}, reconnecting: {e}")

                    sender   = asyncio.create_task(send_audio())
                    pinger   = asyncio.create_task(keepalive())
                    receiver = asyncio.create_task(recv_transcripts())
                    await asyncio.wait(
                        [asyncio.ensure_future(stop_event.wait()), receiver],  # type: ignore
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                    sender.cancel()
                    pinger.cancel()
                    receiver.cancel()
                    await asyncio.gather(sender, pinger, receiver, return_exceptions=True)
                    if stop_event.is_set():
                        break
                    logger.info("🔄 Sarvam session ended. Reconnecting in 2s...")
                    await asyncio.sleep(2)
            except Exception as e:
                if stop_event.is_set():
                    break
                logger.error(f"Sarvam error: {e} — retrying in 5s...")
                await asyncio.sleep(5)
    finally:
        import time as _pa_t
        _chunk_secs = CHUNK / max(RATE, 1)
        _pa_t.sleep(_chunk_secs + 0.05)   # let in-flight executor read() return
        if stream:
            try:
                if sys.platform == "darwin":
                    stream.abort_stream()   # immediate — no drain wait
                else:
                    stream.stop_stream()
            except Exception:
                pass
            _pa_t.sleep(0.05)
            try:
                stream.close()
            except Exception:
                pass
        _pa_t.sleep(0.1)
        try:
            audio.terminate()
        except Exception:
            pass


# ── ASSEMBLYAI UNIVERSAL-3 PRO STREAMING ─────────────────────────────────────
async def stream_audio_assemblyai(controller, is_secondary: bool = False):
    """Stream audio to AssemblyAI and feed transcripts through the detection pipeline.

    When is_secondary=True, uses the secondary language/parser globals so it can
    run in parallel with a primary stream (Dual STT mode).
    """
    global full_sermon_transcript, full_sermon_transcript_secondary, _last_transcript_time

    import pyaudio

    # ── Resolve which language + parser to use for this stream ────────────────
    if is_secondary:
        _lang   = SECONDARY_LANGUAGE or "en"
        _parser = SECONDARY_PARSER
    else:
        _lang   = AAI_LANGUAGE
        _parser = None   # _process_transcript_blob uses PRIMARY_PARSER internally

    audio  = pyaudio.PyAudio()
    stream = None

    try:
        mic_info = audio.get_device_info_by_index(MIC_INDEX)
        logger.info(f"Using: [{MIC_INDEX}] {mic_info['name']}")
        if "stereo mix" in mic_info["name"].lower():
            logger.warning(
                "⚠️ Stereo Mix selected — ALL desktop audio will be captured. "
                "Non-church audio may trigger false detections."
            )
        stream = audio.open(
            format=pyaudio.paInt16, channels=1, rate=RATE,
            input=True, input_device_index=MIC_INDEX,
            frames_per_buffer=CHUNK,
        )
        logger.info("Microphone opened")
    except Exception as e:
        logger.error(f"Microphone error: {e}")
        return

    # ── Import AssemblyAI SDK (lazy — not everyone installs it) ──────────────
    try:
        import assemblyai as aai
        from assemblyai.streaming.v3 import (
            StreamingClient,
            StreamingClientOptions,
            StreamingParameters,
            StreamingEvents,
            TurnEvent,
            BeginEvent,
        )
    except ImportError as _aai_err:
        logger.error(
            f"❌ AssemblyAI SDK not installed or version too old. Run: pip install -U assemblyai  (detail: {_aai_err})"
        )
        return

    loop          = asyncio.get_event_loop()
    partial_context = [""]

    # threading.Event mirror of stop_event so the blocking audio generator can
    # exit cleanly without polling the asyncio Event from a non-async thread.
    _stop_mirror  = threading.Event()

    # asyncio.Queue bridges transcript strings from the SDK callback thread to
    # the async consumer loop below.
    _transcript_queue: asyncio.Queue = asyncio.Queue()

    # ── Reconnect loop — mirrors Sarvam's pattern ─────────────────────────────
    while not stop_event.is_set():

        # Reset stop mirror for this attempt
        _stop_mirror.clear()

        # ── Audio generator (runs inside the executor thread) ─────────────────
        def _audio_generator():
            """Yield raw PCM chunks from the mic until stop is requested."""
            while not _stop_mirror.is_set() and not stop_event.is_set():
                try:
                    yield stream.read(CHUNK, exception_on_overflow=False)
                except Exception:
                    break

        # ── Event callbacks (called from SDK thread) ──────────────────────────
        def _on_turn(client: StreamingClient, event: TurnEvent):
            """Fired by the SDK on every word addition AND at end of turn.
            We only want the final formatted sentence — ignore partials."""
            if not event.end_of_turn:
                return
            sentence = (event.transcript or "").strip()
            if not sentence:
                return
            # Bridge to the asyncio event loop safely
            loop.call_soon_threadsafe(_transcript_queue.put_nowait, sentence)

        def _on_error(client: StreamingClient, error: Exception):
            logger.error(f"⚠️ AssemblyAI streaming error: {error}")
            # Signal the audio generator to stop; outer loop will reconnect
            _stop_mirror.set()

        def _on_session_information(client: StreamingClient, info: BeginEvent):
            logger.info(f"🎤 AssemblyAI session: {info.id}")

        # ── Speech model selection based on language ──────────────────────────
        # u3-rt-pro is English-only; multilingual model handles hi / ml / multi.
        if _lang in ("hi", "ml", "multi"):
            _aai_model   = "universal-streaming-multilingual"
            _lang_detect = _lang == "multi"   # auto-detect for multi mode
        else:
            _aai_model   = "u3-rt-pro"
            _lang_detect = False

        params = StreamingParameters(
            sample_rate=RATE,
            speech_model=_aai_model,
            format_turns=True,
            language_detection=_lang_detect or None,
            min_turn_silence=300,   # 300 ms of silence commits the turn naturally
        )
        client_opts = StreamingClientOptions(
            api_key=ASSEMBLYAI_API_KEY,
            base_url="wss://streaming.assemblyai.com/v3/ws",
        )
        client = StreamingClient(client_opts)
        client.on(StreamingEvents.Turn,               _on_turn)
        client.on(StreamingEvents.Error,              _on_error)
        client.on(StreamingEvents.Begin,               _on_session_information)

        _model_label = {
            "u3-rt-pro":                      "Universal-3 Pro (English)",
            "universal-streaming-multilingual":"Universal-3 Multilingual",
        }.get(_aai_model, _aai_model)
        _stream_tag = "AAI-SEC" if is_secondary else "AAI"
        logger.info(f"🎤 [{_stream_tag}] Connecting — {_model_label} / lang={_lang}...")

        # ── Run blocking SDK call in executor ─────────────────────────────────
        def _run_client():
            try:
                client.connect(params)
                client.stream(_audio_generator())
            except Exception as exc:
                if not stop_event.is_set():
                    logger.error(f"AssemblyAI client error: {exc}")
            finally:
                _stop_mirror.set()   # unblock generator if still running

        executor_future = loop.run_in_executor(None, _run_client)

        # ── Periodic force_endpoint task ──────────────────────────────────────
        # AAI's universal-3 model only fires end_of_turn when the speaker
        # pauses naturally.  For continuous speech (long sentences, preachers
        # who don't breathe), we kick force_endpoint() every N seconds so
        # the turn is always committed within AAI_TURN_CUTOFF_SEC.
        async def _force_endpoint_loop():
            """Every AAI_TURN_CUTOFF_SEC seconds, force the current turn to close."""
            try:
                while not stop_event.is_set() and not _stop_mirror.is_set():
                    await asyncio.sleep(AAI_TURN_CUTOFF_SEC)
                    if stop_event.is_set() or _stop_mirror.is_set():
                        break
                    try:
                        await loop.run_in_executor(None, client.force_endpoint)
                    except Exception:
                        pass  # ignore if session already closed
            except asyncio.CancelledError:
                pass

        _force_task = asyncio.ensure_future(_force_endpoint_loop())

        # ── Async consumer: drain the transcript queue ────────────────────────
        try:
            while not stop_event.is_set():
                try:
                    # Use a short timeout so we notice stop_event promptly
                    sentence = await asyncio.wait_for(
                        _transcript_queue.get(), timeout=0.5
                    )
                except asyncio.TimeoutError:
                    # No transcript yet; check if the executor finished (error/disconnect)
                    if  executor_future.done():
                        break
                    continue

                if not sentence:
                    continue

                _stream_tag = "AAI-SEC" if is_secondary else "AAI"
                logger.info(f"📝 [{_stream_tag}] {sentence}")
                _last_transcript_time = time.time()

                if is_secondary:
                    full_sermon_transcript_secondary += " " + sentence.strip()
                    _process_transcript_blob(
                        sentence, partial_context, controller,
                        is_secondary=True
                    )
                else:
                    full_sermon_transcript += " " + sentence.strip()
                    _process_transcript_blob(sentence, partial_context, controller)

        finally:
            # Cancel the periodic force_endpoint task first
            _force_task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(_force_task), timeout=1.0)
            except Exception:
                pass
            # Stop audio generator first so stream() returns quickly
            _stop_mirror.set()
            # disconnect(terminate=True) sends a TerminateSession message which
            # causes the server to close the WebSocket, unblocking the SDK's
            # internal read/write threads so join() returns cleanly.
            # Run in executor because join() can take up to ~1s even when clean.
            async def _safe_disconnect():
                try:
                    await loop.run_in_executor(
                        None, lambda: client.disconnect(terminate=True)
                    )
                except Exception:
                    pass
            try:
                await asyncio.wait_for(_safe_disconnect(), timeout=4.0)
            except Exception:
                pass
            try:
                await asyncio.wait_for(executor_future, timeout=3.0)
            except Exception:
                pass

        if stop_event.is_set():
            break

        _stream_tag = "AAI-SEC" if is_secondary else "AAI"
        logger.info(f"🔄 [{_stream_tag}] Session ended. Reconnecting in 2s...")
        await asyncio.sleep(2)

    # ── Microphone teardown — identical to stream_audio() ────────────────────
    import time as _pa_t
    _chunk_secs = CHUNK / max(RATE, 1)
    _pa_t.sleep(_chunk_secs + 0.05)
    if stream:
        try:
            if sys.platform == "darwin":
                stream.abort_stream()
            else:
                stream.stop_stream()
        except Exception:
            pass
        _pa_t.sleep(0.05)
        try:
            stream.close()
        except Exception:
            pass
    _pa_t.sleep(0.1)
    try:
        audio.terminate()
    except Exception:
        pass


# ── SILENCE WATCHDOG (Feature 6) ──────────────────────────────────────────────
async def _silence_watchdog():
    """Feature 6: auto-stop engine if no transcript line arrives within SILENCE_TIMEOUT seconds."""
    global _last_transcript_time
    _last_transcript_time = time.time()   # reset at session start
    while not stop_event.is_set():
        await asyncio.sleep(5)
        if SILENCE_TIMEOUT > 0 and time.time() - _last_transcript_time > SILENCE_TIMEOUT:
            logger.info(f"⏱️ Auto-stopped: {SILENCE_TIMEOUT}s audio inactivity detected")
            _shutdown_flag.set()  # BUG 2: Signal all background threads to exit before teardown
            stop_event.set()
            return


# ── MAIN ──────────────────────────────────────────────────────────────────────
async def main():
    global stop_event, engine_loop, _controller
    stop_event  = asyncio.Event()
    engine_loop = asyncio.get_event_loop()

    panic_listener = None

    if IS_WINDOWS and PANIC_KEY:
        try:
            from pynput import keyboard as pynput_kb

            def on_press(key):
                try:
                    k = key.char
                except AttributeError:
                    k = key.name
                if k == PANIC_KEY:
                    trigger_panic()

            panic_listener = pynput_kb.Listener(on_press=on_press)
            panic_listener.daemon = True
            panic_listener.start()
            logger.info(f"🚨 Panic key active: '{PANIC_KEY}'")
        except Exception as e:
            logger.warning(f"⚠️ Could not bind panic key: {e}")
    elif not IS_WINDOWS:
        logger.info("🚨 macOS: use Shift+Escape in the app window")

    _controller = VerseController()
    connected   = False

    for attempt in range(1, 6):
        logger.info(f"Connection attempt {attempt}/5...")
        if stop_event.is_set():  # type: ignore
            logger.info("Stop requested — aborting connection.")
            return
        if _controller.connect():
            connected = True
            break
        if stop_event.is_set():  # type: ignore
            return
        if attempt < 5:
            logger.warning("Retrying in 5s...")
            await asyncio.sleep(5)

    if not connected:
        logger.error("Could not connect to VerseView after 5 attempts.")
        return

    # ── Start Discord-bot bridge (port 50011) ─────────────────────────────────
    if _start_bot_bridge is not None:
        try:
            _start_bot_bridge(_controller, port=50011, gui_app=_gui_app)
            logger.info("Bot bridge started — controller injected")
            if BRIDGE_READY_CALLBACK:
                BRIDGE_READY_CALLBACK()
        except Exception as _bridge_err:
            logger.warning(f"⚠️ Bot bridge failed to start: {_bridge_err}")

    logger.info("=" * 60)
    logger.info("🚀 VerseView Live Started")
    if USE_SARVAM:
        _engine_label = "Sarvam AI (Malayalam)"
    elif STT_ENGINE == "assemblyai":
        _engine_label = (
            "AssemblyAI Universal-3 Multilingual"
            if AAI_LANGUAGE == "multi"
            else "AssemblyAI Universal-3 Pro"
        )
    else:
        _engine_label = "Deepgram"
    logger.info(f"   Engine: {_engine_label}")
    logger.info("=" * 60)

    try:
        points_task   = asyncio.create_task(live_points_loop())
        watchdog_task = asyncio.create_task(_silence_watchdog())

        # ── Primary stream task ───────────────────────────────────────────────
        if USE_SARVAM:
            primary_task = asyncio.create_task(stream_audio_sarvam(_controller, is_secondary=False))
        elif STT_ENGINE == "assemblyai":
            primary_task = asyncio.create_task(stream_audio_assemblyai(_controller))
        else:
            primary_task = asyncio.create_task(stream_audio(_controller, is_secondary=False))

        # ── Optional secondary stream task ────────────────────────────────────
        secondary_task = None
        if DUAL_STT_ENABLED and SECONDARY_LANGUAGE:
            if SECONDARY_USE_SARVAM:
                secondary_task = asyncio.create_task(stream_audio_sarvam(_controller, is_secondary=True))
            elif SECONDARY_STT_ENGINE == "assemblyai":
                secondary_task = asyncio.create_task(stream_audio_assemblyai(_controller, is_secondary=True))
            else:
                secondary_task = asyncio.create_task(stream_audio(_controller, is_secondary=True))
            logger.info(f"🌐 Secondary STT stream started (lang={SECONDARY_LANGUAGE}, engine={SECONDARY_STT_ENGINE})")

        # Wait for stop signal, then cancel all stream tasks
        await stop_event.wait()
        primary_task.cancel()
        if secondary_task:
            secondary_task.cancel()

        tasks_to_gather = [primary_task]
        if secondary_task:
            tasks_to_gather.append(secondary_task)
        await asyncio.gather(*tasks_to_gather, return_exceptions=True)
    finally:
        # BUG 2: Set shutdown flag FIRST so background threads can see it and exit
        _shutdown_flag.set()
        # Join all active background threads with timeout before tearing down shared resources
        for _bg_t in list(_active_bg_threads):
            try:
                _bg_t.join(timeout=2)
            except Exception:
                pass
        _active_bg_threads.clear()

        try:
            points_task.cancel()
        except Exception:
            pass
        try:
            watchdog_task.cancel()
        except Exception:
            pass
        if panic_listener:
            try:
                panic_listener.stop()
            except Exception:
                pass
        if _controller:
            try:
                _controller.cleanup()
            except Exception:
                pass
        _controller = None
        logger.info(f"📊 LLM calls: {LLM_CALL_COUNT}")
        logger.info("Shutdown complete")
        _discord_live_log.stop()


if __name__ == "__main__":
    asyncio.run(main())