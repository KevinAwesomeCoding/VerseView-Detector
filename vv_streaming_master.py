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

from parse_reference_eng import parse_references as parse_eng, normalize_numbers_only as norm_eng, resolve_book as resolve_book_eng
from parse_reference_hindi import parse_references as parse_hindi, normalize_numbers_only as norm_hindi
from parse_reference_ml import parse_references as parse_ml, normalize_numbers_only as norm_ml
from bible_fetcher import fetch_verse as multi_fetch


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
class _CerebrasCompletions:
    def __init__(self, api_key): self._key = api_key

    def create(self, model, messages, temperature=0.2, max_tokens=None, **kw):
        headers = {"Authorization": f"Bearer {self._key}", "Content-Type": "application/json"}
        body    = {"model": model, "messages": messages, "temperature": temperature}
        if max_tokens is not None:
            body["max_completion_tokens"] = max_tokens
        r = requests.post(
            "https://api.cerebras.ai/v1/chat/completions",
            headers=headers, json=body, timeout=60, verify=certifi.where(),
        )
        r.raise_for_status()
        return _GroqResponse(r.json()["choices"][0]["message"]["content"])

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
        self._msg_id   = None
        self._lines    = []
        self._dirty    = False
        self._lock     = threading.Lock()
        self._stop_evt = threading.Event()
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
            caption = f"📋 **VerseView Session Log** — {label}"
            
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

    def stop(self):
        self._stop_evt.set()
        self._delete()
        self._upload_log_file()


class _DiscordLogHandler(logging.Handler):
    def __init__(self, live_log):
        super().__init__()
        self._live = live_log

    def emit(self, record):
        if not DISCORD_LOG_WEBHOOK_URL:
            return
        try:
            import datetime as _dt
            if record.levelno >= logging.INFO:
                self._live.append(
                    f"{_dt.datetime.now().strftime('%H:%M:%S')} {record.getMessage()}"
                )
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
DEEPGRAM_LANGUAGE     = "en"
DEEPGRAM_MODEL        = "nova-2"
SARVAM_LANGUAGE       = "ml-IN"
PRIMARY_PARSER        = parse_eng
MIC_INDEX             = 1
RATE                  = 16000
CHUNK                 = 4096
REMOTE_URL            = "http://localhost:50010/control.html"
DEDUP_WINDOW          = 60
COOLDOWN              = 3.0
LLM_ENABLED           = True
LLM_CALL_COUNT        = 0
_llm_in_flight = False
_llm_last_key = None
_llm_last_time = 0.0
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

VERSE_INTERRUPT_ENABLED = False

# ── LLM CLIENTS (initialised in configure()) ─────────────────────────────────
groq_client     = None   # verse extraction only            (Groq llama-3.1-8b-instant)
cerebras_client = None   # live outline + summary fallback  (Cerebras gpt-oss-120b)
mistral_client  = None   # sermon summary primary           (Mistral mistral-large-latest)

# ── GLOBALS & SERMON BUFFER ──────────────────────────────────────────────────
stop_event             = None
engine_loop            = None
_controller            = None
full_sermon_transcript = ""
verses_cited           = []


# ── STOP & PANIC ─────────────────────────────────────────────────────────────
def request_stop():
    global stop_event, engine_loop
    if engine_loop and stop_event:
        engine_loop.call_soon_threadsafe(stop_event.set)
    logger.info("🛑 Stop requested from GUI.")


def trigger_panic():
    global _controller
    if _controller:
        _controller.close_presentation()


# ── SMART AMEN ───────────────────────────────────────────────────────────────
def check_smart_amen(text, controller):
    if not SMART_AMEN_ENABLED:
        return False
    text_lower = text.lower()
    for kw in SMART_AMEN_KEYWORDS:
        if kw in text_lower:
            logger.info(f"🙏 Smart Amen triggered by phrase: '{kw}'")
            controller.close_presentation()
            return True
    return False


# ── LIVE POINTS LOOP  (Cerebras → Groq fallback) ─────────────────────────────
async def live_points_loop():
    global full_sermon_transcript, LLM_ENABLED, groq_client, cerebras_client
    global LIVE_POINTS_PROMPT, LIVE_POINTS_CALLBACK, LIVE_POINTS_GET_CURRENT_CB

    last_processed_length = 0

    while not stop_event.is_set():
        await asyncio.sleep(90)

        if not LLM_ENABLED or (not cerebras_client and not groq_client) or not LIVE_POINTS_CALLBACK:
            continue

        current_transcript = full_sermon_transcript.strip()
        if len(current_transcript) < 150 or len(current_transcript) <= last_processed_length + 50:
            continue

        last_processed_length = len(current_transcript)

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
                _client = cerebras_client or groq_client
                if _client is None:
                    return None
                response = _client.chat.completions.create(  # type: ignore
                    model=("gpt-oss-120b" if cerebras_client else "llama-3.3-70b-versatile"),
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.choices[0].message.content.strip()

            points = await engine_loop.run_in_executor(None, fetch_points)  # type: ignore
            if points:
                LIVE_POINTS_CALLBACK(points)  # type: ignore
        except Exception as e:
            logger.error(f"Live points generation failed: {e}")


# ── SERMON SUMMARY  (Mistral → Cerebras → Groq) ──────────────────────────────
def generate_sermon_summary():
    global full_sermon_transcript, verses_cited, LLM_ENABLED
    global groq_client, cerebras_client, mistral_client

    if not LLM_ENABLED or (not mistral_client and not cerebras_client and not groq_client):
        return "⚠️ LLM disabled — add a Mistral, Cerebras, or Groq API key to generate summaries."

    if len(full_sermon_transcript.strip()) < 100:
        return "⚠️ Transcript is too short to generate a meaningful summary."

    import datetime
    today_str = datetime.datetime.now().strftime("%B %d, %Y  ·  %I:%M %p")

    prompt = (
        "You are an expert sermon note-taker. Read the following sermon transcript "
        "and generate structured sermon notes using the exact Markdown format below. "
        "IMPORTANT: If the transcript contains any other languages (such as Malayalam, Hindi, or others), "
        "you must translate those portions and write the final output strictly in English.\n\n"
        "Extract the information from the transcript as best as you can.\n\n"
        "---FORMAT TEMPLATE START---\n"
        f"## 📅 {today_str} | [Sermon Series Name if mentioned]\n"
        "**Title:** [Create a short, compelling title]\n"
        "**Speaker:** [Speaker Name if mentioned]\n\n"
        "### 📖 Primary Scripture\n"
        "**Main Passage:** [Identify the core passage]\n"
        "**Key Verse:** [Quote the most central verse from the transcript]\n\n"
        "### 💡 The Big Idea\n"
        "* [In one clear sentence, summarize the absolute 'bottom line' of the message]\n\n"
        "### 📝 Main Points & Observations\n"
        "[Identify 3 main points from the sermon. For each point, use this exact structure:]\n"
        "**1. [Point Name]**\n"
        "* **Supporting Scripture:** [Reference if any]\n"
        "* **Notes:** [Brief 1-2 sentence summary of this point]\n"
        "* *Key Thought:* [One standout quote or idea from this section]\n\n"
        "### ❓ Questions & Reflections\n"
        "* **Reflection:** [Generate one challenging question based on the sermon for the listener]\n\n"
        "### 🏃\u200d♂️ The 'So What?' (Application)\n"
        "1. **Immediate Step:** [A practical action step the listener can do this week]\n"
        "2. **Prayer Focus:** [A short prayer prompt related to the message]\n"
        "---FORMAT TEMPLATE END---\n\n"
        f"Transcript:\n{full_sermon_transcript}\n"
    )

    try:
        if mistral_client:
            _which = "Mistral mistral-large-latest"
            _model = "mistral-large-latest"
        elif cerebras_client:
            _which = "Cerebras gpt-oss-120b"
            _model = "gpt-oss-120b"
        else:
            _which = "Groq llama-3.3-70b-versatile"
            _model = "llama-3.3-70b-versatile"

        logger.info(f"⏳ Generating Sermon Cliff Notes via {_which}...")
        _client  = mistral_client or cerebras_client or groq_client
        if _client is None:
            return "⚠️ LLM disabled — add a Mistral, Cerebras, or Groq API key to generate summaries."
        response = _client.chat.completions.create(  # type: ignore
            model=_model,
            messages=[{"role": "user", "content": prompt}],
        )
        summary = response.choices[0].message.content.strip()

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
    logger.info("🗑️ Sermon memory has been manually cleared.")


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
    panic_key="esc", smart_amen=True,
    live_points_prompt="", live_points_callback=None, live_points_get_current_cb=None,
):
    global DEEPGRAM_API_KEY, GROQ_API_KEY, GEMINI_API_KEY, CEREBRAS_API_KEY, MISTRAL_API_KEY, SARVAM_API_KEY
    global DISCORD_WEBHOOK_URL, DISCORD_LOG_WEBHOOK_URL, DISCORD_NOTES_WEBHOOK_URL
    global USE_SARVAM, DEEPGRAM_LANGUAGE, DEEPGRAM_MODEL, SARVAM_LANGUAGE
    global PRIMARY_PARSER, MIC_INDEX, RATE, CHUNK, REMOTE_URL
    global DEDUP_WINDOW, COOLDOWN, LLM_ENABLED, BIBLE_TRANSLATION, USE_XPATH
    global groq_client, cerebras_client, mistral_client
    global CONFIDENCE_THRESHOLD, REQUIRE_MANUAL_CONFIRM, CONFIRM_CALLBACK, REQUIRE_VERIFY, PANIC_KEY, SMART_AMEN_ENABLED
    global full_sermon_transcript, verses_cited
    global LIVE_POINTS_PROMPT, LIVE_POINTS_CALLBACK, LIVE_POINTS_GET_CURRENT_CB
    global normalize_numbers_only
    _cancel_vtc()

    # NOTE: Sermon buffer is intentionally NOT reset here so memory persists across stops/starts!
    global _llm_in_flight
    _llm_in_flight = False

    DEEPGRAM_API_KEY = deepgram_api_key
    GROQ_API_KEY     = groq_api_key
    GEMINI_API_KEY   = gemini_api_key
    CEREBRAS_API_KEY = cerebras_api_key
    MISTRAL_API_KEY  = mistral_api_key
    SARVAM_API_KEY   = sarvam_api_key

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
    VERSE_INTERRUPT_ENABLED = verse_interrupt
    LIVE_POINTS_PROMPT         = live_points_prompt
    LIVE_POINTS_CALLBACK       = live_points_callback
    LIVE_POINTS_GET_CURRENT_CB = live_points_get_current_cb

    if language == "en":
        USE_SARVAM             = False
        DEEPGRAM_LANGUAGE      = "en"
        DEEPGRAM_MODEL         = "nova-2"
        PRIMARY_PARSER         = parse_eng
        normalize_numbers_only = norm_eng
    elif language == "hi":
        USE_SARVAM             = False
        DEEPGRAM_LANGUAGE      = "hi"
        DEEPGRAM_MODEL         = "nova-3"
        PRIMARY_PARSER         = parse_hindi
        normalize_numbers_only = norm_hindi
    elif language == "ml":
        USE_SARVAM             = True
        SARVAM_LANGUAGE        = "ml-IN"
        PRIMARY_PARSER         = parse_ml
        normalize_numbers_only = norm_ml
    else:
        USE_SARVAM             = False
        DEEPGRAM_LANGUAGE      = "multi"
        DEEPGRAM_MODEL         = "nova-2"
        PRIMARY_PARSER         = parse_eng
        normalize_numbers_only = norm_eng


# ── CONTEXT TRACKING ─────────────────────────────────────────────────────────
current_book    = None
current_chapter = None
current_verse   = None


def get_context() -> dict:
    return {"book": current_book or "", "chapter": current_chapter or "", "verse": current_verse or ""}


def set_context(book: str, chapter: str, verse: str):
    global current_book, current_chapter, current_verse
    current_book    = book.strip()    or None
    current_chapter = chapter.strip() or None
    current_verse   = verse.strip()   or None
    logger.info(f"Context manually set: {current_book} {current_chapter}:{current_verse}")


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
    return None


# ── VERSE INTERRUPT (wait for speaker to say verse, then display; 60s timeout; cancel on new ref) ─
def deliver_verse(ref: str, controller, bypass_cooldown=False, confidence=1.0):
    """
    Deliver a detected verse: if Verse Interrupt is on, wait for the speaker to say the verse
    (fetch text via Bible API, listen for trigger words, 60s timeout; new ref cancels current).
    Otherwise send directly to controller.
    """
    if VERSE_INTERRUPT_ENABLED:
        _start_vtc(ref, controller)
    else:
        controller.send_verse(ref, bypass_cooldown=bypass_cooldown, confidence=confidence)


# ── ONWARDS MODE ──────────────────────────────────────────────────────────────
onwards_active     = False
onwards_book       = None
onwards_chapter    = None
onwards_verse      = None
onwards_timer      = None
onwards_target_ref = None
onwards_trigger    = None
onwards_target_text = None


def _stop_onwards():
    global onwards_active, onwards_timer, onwards_target_ref, onwards_trigger
    onwards_active     = False
    if onwards_timer:
        onwards_timer.cancel()
    onwards_timer      = None
    onwards_target_ref = None
    onwards_trigger    = None
    logger.info("⏹️ ONWARDS mode stopped")

def _cancel_vtc():
    global _vtc_pending_ref, _vtc_trigger_words, _vtc_timer
    if _vtc_timer:
        _vtc_timer.cancel()
    _vtc_pending_ref   = None
    _vtc_trigger_words = []
    _vtc_timer         = None

def _start_vtc(ref, controller):
    """Fetch verse text via Bible API, then use LLM semantic check to confirm it was spoken. New ref cancels previous."""
    global _vtc_pending_ref, _vtc_trigger_words, _vtc_timer
    
    if _vtc_pending_ref == ref:
        return # Ignore duplicate detections of the same verse we are already waiting for
        
    _cancel_vtc()  # void any previous pending ref (cancel-on-new-ref)

    text = fetch_verse_text(ref)
    if not text:
        logger.warning(f"⚠️ VTC: Could not fetch text for {ref}. Sending instantly.")
        controller.send_verse(ref, bypass_cooldown=True)
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
_vtc_last_excerpt = ""

def check_vtc(text, controller) -> bool:
    """Call this on every transcript blob. Returns True if VTC matched and sent."""
    global _vtc_pending_ref, _vtc_semantic_in_flight, _vtc_last_excerpt
    if not _vtc_pending_ref or not _vtc_trigger_words:
        return False
    verse_text = _vtc_trigger_words[0]
    excerpt    = _excerpt_since_last_advance(40)
    
    if cerebras_client and excerpt:
        if _vtc_semantic_in_flight:
            return False  # already checking; result will come
        if excerpt == _vtc_last_excerpt:
            return False  # transcript hasn't changed since last check
            
        current_ref = _vtc_pending_ref
        _vtc_semantic_in_flight = True
        _vtc_last_excerpt = excerpt
        
        def task():
            global _vtc_semantic_in_flight, _vtc_last_excerpt
            try:
                if _llm_semantic_match(verse_text, excerpt, label=current_ref):
                    if _vtc_pending_ref == current_ref:
                        logger.info(f"✅ VTC confirmed: {current_ref} (Cerebras)")
                        _cancel_vtc()
                        _mark_advance_offset()
                        controller.send_verse(current_ref, bypass_cooldown=True)
            finally:
                _vtc_semantic_in_flight = False
                _vtc_last_excerpt = ""  # clear so the next new excerpt triggers a fresh check
                
        threading.Thread(target=task, daemon=True).start()
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
_onwards_last_excerpt = ""

def _check_onwards_advance(text, controller) -> bool:
    global onwards_verse, _onwards_semantic_in_flight, _onwards_last_excerpt
    if not onwards_active or not onwards_target_ref or not onwards_target_text:
        return False
        
    excerpt = _excerpt_since_last_advance(40)
    
    if excerpt and cerebras_client:
        if _onwards_semantic_in_flight:
            return False  # already checking; result will come
        if excerpt == _onwards_last_excerpt:
            return False  # transcript unchanged since last check
            
        current_ref = onwards_target_ref
        current_text = onwards_target_text
        _onwards_semantic_in_flight = True
        _onwards_last_excerpt = excerpt
        
        def task():
            global onwards_verse, _onwards_semantic_in_flight, _onwards_last_excerpt
            try:
                if _llm_semantic_match(current_text, excerpt, label=f"ONWARDS {current_ref}"):
                    if onwards_target_ref == current_ref:
                        logger.info(f"🎯 ONWARDS ADVANCE: {current_ref} (Cerebras)")
                        _mark_advance_offset()
                        controller.send_verse(current_ref, bypass_cooldown=True)
                        onwards_verse += 1
                        _reset_onwards_timer()
                        threading.Thread(target=_fetch_next_onwards, daemon=True).start()
            finally:
                _onwards_semantic_in_flight = False
                _onwards_last_excerpt = ""  # clear so next new excerpt triggers a fresh check
                
        threading.Thread(target=task, daemon=True).start()
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
            controller.send_verse(onwards_target_ref, bypass_cooldown=True)
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
                    verse_queue.append((ref, text))
                logger.info(f"📚 Queued: {ref}")

    threading.Thread(target=fetch_all, daemon=True).start()
    logger.info(f"📖 Range queued: {book} {chapter}:{start_verse} → {end_verse}")


_queue_semantic_in_flight = False
_queue_last_excerpt = ""

def check_verse_queue(transcript, controller) -> bool:
    global _queue_semantic_in_flight, _queue_last_excerpt
    with verse_queue_lock:
        if not verse_queue:
            return False
        next_ref, verse_text = verse_queue[0]
        
    excerpt = _excerpt_since_last_advance(40)
    if not excerpt:
        return False
        
    if cerebras_client:
        if _queue_semantic_in_flight:
            return False  # already checking; result will come
        if excerpt == _queue_last_excerpt:
            return False  # transcript unchanged since last check
            
        current_ref = next_ref
        _queue_semantic_in_flight = True
        _queue_last_excerpt = excerpt
        
        def task():
            global _queue_semantic_in_flight, _queue_last_excerpt
            try:
                if _llm_semantic_match(verse_text, excerpt, label=f"QUEUE {current_ref}"):
                    with verse_queue_lock:
                        if verse_queue and verse_queue[0][0] == current_ref:
                            verse_queue.pop(0)
                        else:
                            return  # Queue advanced while we were checking
                    logger.info(f"🎯 AUTO-ADVANCE: {current_ref} (Cerebras)")
                    _mark_advance_offset()
                    controller.send_verse(current_ref, bypass_cooldown=True)
            finally:
                _queue_semantic_in_flight = False
                _queue_last_excerpt = ""  # clear so next new excerpt triggers a fresh check
                
        threading.Thread(target=task, daemon=True).start()
        return False
    # Fallback: no Cerebras client → no auto-advance for this verse
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


# ── LLM VERSE EXTRACTION  (Groq only — llama-3.1-8b-instant) ─────────────────
def extract_verse_with_llm(text):
    global LLM_CALL_COUNT

    if not groq_client:
        return None

    context_hint = ""
    if current_book and current_chapter:
        context_hint = (
            f"\nContext: The speaker is currently reading from "
            f"{current_book} chapter {current_chapter}."
        )

    try:
        LLM_CALL_COUNT += 1
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{
                "role": "user",
                "content": (
                    f"Extract the Bible verse reference from this text. "
                    f"Return ONLY in format Book Chapter:Verse (e.g., John 3:16). "
                    f"If no verse found, return exactly NONE.{context_hint}\nText: {text}"
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
    """Use Cerebras llama3.1-8b to decide if transcript_excerpt corresponds to verse_text (YES/NO)."""
    if not cerebras_client:
        return False
    verse_text = (verse_text or "").strip()
    transcript_excerpt = (transcript_excerpt or "").strip()
    if not verse_text or not transcript_excerpt:
        return False
    logger.info(f"🧠 Cerebras{(' [' + label + ']') if label else ''}: checking '{transcript_excerpt[-60:]}' vs verse")
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
        response = cerebras_client.chat.completions.create(
            model="llama3.1-8b",
            messages=[{"role": "user", "content": prompt}],
        )
        answer = response.choices[0].message.content.strip().upper()
        result = answer.startswith("YES")
        logger.info(f"🧠 Cerebras{(' [' + label + ']') if label else ''}: → {'YES ✅' if result else 'NO ❌'}")
        return result
    except Exception as e:
        logger.error(f"❌ Cerebras semantic match error: {e}")
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

            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
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

    def send_verse(self, ref, bypass_cooldown=False, confidence=1.0):
        global current_book, current_chapter, current_verse, verses_cited
        now = time.time()

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
                        self.send_verse(ref, bypass_cooldown=True, confidence=1.0)
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

        # ── COOLDOWNS ──
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

            self.driver.execute_script("arguments[0].value = arguments[1];", self.box, ref)
            self.driver.execute_script("arguments[0].click();", self.btn)
            logger.info(f"✅ PRESENTED: {ref}")

            if ref not in verses_cited:
                verses_cited.append(ref)

            send_to_discord(ref)

            parts = ref.split()
            if len(parts) >= 2:
                if ":" in parts[-1]:
                    current_book    = " ".join(parts[:-1])
                    current_chapter, current_verse = parts[-1].split(":")
                else:
                    current_book    = " ".join(parts[:-1])
                    current_chapter = parts[-1]
                    current_verse   = None

            self.history[ref] = now
            self.last_sent    = ref
            self.last_time    = now

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
    r"(?:have\s+our\s+attention\s+in\s+the\s+book\s+of"
    r"|have\s+our\s+attention\s+to\s+the\s+book\s+of"
    r"|attention\s+in\s+the\s+book\s+of"
    r"|attention\s+to\s+the\s+book\s+of"
    r"|turn\s+(?:to|in)\s+(?:the\s+)?book\s+of"
    r"|open\s+(?:your\s+)?(?:bibles?\s+)?to\s+(?:the\s+)?book\s+of"
    r"|(?:the\s+)?book\s+of)\s+"
    r"([0-9a-z]+(?:\s+[0-9a-z]+){0,2})",
    re.IGNORECASE,
)


def _apply_book_context_if_mentioned(text: str) -> bool:
    """If text mentions 'book of X' or 'attention in the book of X', set current book and clear chapter/verse. Returns True if context was set."""
    global current_book, current_chapter, current_verse
    m = BOOK_CONTEXT_PHRASES.search(text)
    if not m:
        return False
    raw = m.group(1).strip()
    book = resolve_book_eng(raw)
    if book:
        current_book = book
        current_chapter = None
        current_verse = None
        logger.info(f"📖 Book context set to: {book} (from ‘…book of {raw}…’)")
        return True
    return False


def detect_verse_hybrid(text, controller, confidence=1.0) -> bool:
    global current_book, current_chapter, current_verse

    if not text or len(text.strip()) < 3:
        return False

    fixes = {
        r"\b(?:sam's|sams|sam)\b": "psalms",
        r"\bnayan\b":              "nine",
    }
    for pattern, replacement in fixes.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    def trigger_onwards_if_needed(ref_string, original_text):
        if any(kw in original_text.lower() for kw in ONWARDS_KEYWORDS):
            parts = ref_string.split()
            if ":" in parts[-1]:
                ch, vs = parts[-1].split(":")
                bk     = " ".join(parts[:-1])
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
        num_norm = re.sub(
            r'\b(20|30|40|50|60|70|80|90)\s+([1-9])\b',
            lambda m: str(int(m.group(1)) + int(m.group(2))),
            num_norm,
        )

        # Context helper — if we already know the book but not the chapter,
        # allow "chapter 3" / "ch 3" to set chapter context (prevents LLM spam on chapter-only blobs).
        if current_book and not current_chapter:
            m_ch = re.search(r'\b(?:chapter|chap|ch)\s+(\d{1,3})\b', num_norm.lower())
            if m_ch:
                current_chapter = m_ch.group(1)
                current_verse   = None
                logger.info(f"📌 Chapter context set: {current_book} {current_chapter}")

        # Layer 1 — parser
        refs = PRIMARY_PARSER(text)
        if refs:
            verse      = refs[0]
            is_blocked = False
            if ":" not in verse:
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
                logger.info(f"🔍 PARSER: {verse} ({int(confidence*100)}% Acc)")
                deliver_verse(verse, controller, bypass_cooldown=False, confidence=confidence)
                trigger_onwards_if_needed(verse, text)
                if ":" in verse:
                    check_and_queue_range(text, verse, controller)
                return True

        # Layer 2 — contextual (number only, same book/chapter)
        m = re.search(r'\b(\d+)\b', num_norm)
        if m and current_book and current_chapter:
            candidate  = m.group(1)
            text_lower = num_norm.lower()
            is_valid   = False
            if len(text.split()) <= 2:
                is_valid = True
            elif re.search(r'\b(?:verse|verses|v|vs)\s+' + candidate + r'\b', text_lower):
                is_valid = True
            elif re.search(r'\b' + re.escape(candidate) + r'\s*(?:st|nd|rd|th)?\s+verse\b', text_lower):
                is_valid = True
            elif re.search(r'\b(?:back|return|going)\b', text_lower) and re.search(r'\bverse\b', text_lower):
                is_valid = True
            elif any(kw in text_lower for kw in ["വാക്യം", "വചനം", "വചന", "वचन", "पद"]):
                is_valid = True
            if is_valid:
                ref = f"{current_book} {current_chapter}:{candidate}"
                logger.info(f"🔍 CONTEXTUAL: {ref} ({int(confidence*100)}% Acc)")
                deliver_verse(ref, controller, bypass_cooldown=False, confidence=confidence)
                trigger_onwards_if_needed(ref, text)
                check_and_queue_range(num_norm, ref, controller)
                return True

        # Layer 3 — Hindi devanagari digits
        m_hi = re.search(r'([\u0966-\u096F]+)', text)
        if m_hi and current_book and current_chapter:
            ref = f"{current_book} {current_chapter}:{m_hi.group(1)}"
            logger.info(f"🔍 HINDI CTX: {ref} ({int(confidence*100)}% Acc)")
            deliver_verse(ref, controller, bypass_cooldown=False, confidence=confidence)
            trigger_onwards_if_needed(ref, text)
            return True

        # Layer 4 — Malayalam digits
        m_ml = re.search(r'([\u0D66-\u0D6F]+)', text)
        if m_ml and current_book and current_chapter:
            ref = f"{current_book} {current_chapter}:{m_ml.group(1)}"
            logger.info(f"🔍 MALAYALAM CTX: {ref} ({int(confidence*100)}% Acc)")
            deliver_verse(ref, controller, bypass_cooldown=False, confidence=confidence)
            trigger_onwards_if_needed(ref, text)
            return True

        # Layer 5 — sequential (next verse)
        if current_book and current_chapter and current_verse:
            m_num = re.search(r'\b(\d{1,3})\b', num_norm)
            if m_num:
                candidate = m_num.group(1)
                try:
                    if int(candidate) == int(current_verse) + 1:
                        ref = f"{current_book} {current_chapter}:{candidate}"
                        logger.info(f"🔍 SEQUENTIAL: {ref} ({int(confidence*100)}% Acc)")
                        deliver_verse(ref, controller, bypass_cooldown=False, confidence=confidence)
                        trigger_onwards_if_needed(ref, text)
                        return True
                except ValueError:
                    pass

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
                if not any(text_after.startswith(b) for b in blockers):
                    if 1 <= start_v < end_v <= start_v + 30:
                        ref_start = f"{current_book} {current_chapter}:{start_v}"
                        logger.info(
                            f"🔍 RANGE: {current_book} {current_chapter}:{start_v}→{end_v} "
                            f"({int(confidence*100)}% Acc)"
                        )
                        deliver_verse(ref_start, controller, bypass_cooldown=False, confidence=confidence)
                        queue_verse_range(current_book, current_chapter, start_v, end_v, controller)
                        trigger_onwards_if_needed(ref_start, text)
                        return True

        # Layer 8 — simple "Book chapter" pattern
        m_simple = re.search(
            r'\b((?:[1-3]\s*)?(?:' + '|'.join(BOOK_KEYWORDS[:40]) + r'))\s+(\d{1,3})\b',
            text, re.IGNORECASE,
        )
        if m_simple:
            ref = f"{m_simple.group(1).strip().title()} {m_simple.group(2)}"
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

        if not has_book and not has_number:
            return False
                # Require BOTH a book name AND a number before burning an LLM call
        if not (has_book and has_number):
            return False

        # Need at least 6 words so context is rich enough for LLM
        if len(text.split()) < 6:
            return False

        global _llm_in_flight
        if _llm_in_flight:
            return False  # let partial_context keep growing instead

        # Avoid retrying the LLM on essentially the same rolling context over and over.
        global _llm_last_key, _llm_last_time
        llm_key = re.sub(r'\s+', ' ', text_lower).strip()[-220:]
        now_ts  = time.time()
        if _llm_last_key == llm_key and (now_ts - _llm_last_time) < 25:
            return False
        _llm_last_key  = llm_key
        _llm_last_time = now_ts

        logger.info(f"📞 LLM: '{text[:80]}'")
        _llm_in_flight = True

        def llm_task():
            global _llm_in_flight
            try:
                verse = extract_verse_with_llm(text)
                if verse:
                    deliver_verse(verse, controller, bypass_cooldown=False, confidence=confidence)
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


def _process_transcript_blob(sentence: str, partial_context_ref: list, controller):
    partial_context = partial_context_ref[0]
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
        found = detect_verse_hybrid(partial_context.strip(), controller, confidence=1.0)
        if found:
            partial_context = ""
            break
    if partial_context:
        words = partial_context.split()
        if len(words) > 50:
            partial_context = " ".join(words[-25:])
    partial_context_ref[0] = partial_context


# ── DEEPGRAM STREAMING ────────────────────────────────────────────────────────
async def stream_audio(controller):
    global full_sermon_transcript
    import websockets
    import json

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

    url = (
        f"wss://api.deepgram.com/v1/listen"
        f"?language={DEEPGRAM_LANGUAGE}"
        f"&model={DEEPGRAM_MODEL}"
        f"&punctuate=true"
        f"&smart_format=false"
        f"&interim_results=true"
        f"&utterance_end_ms=1000"
        f"&endpointing=300"
        f"&encoding=linear16"
        f"&sample_rate={RATE}"
    )
    headers = {"Authorization": f"Token {DEEPGRAM_API_KEY}"}
    loop    = asyncio.get_event_loop()

    def read_audio():
        return stream.read(CHUNK, exception_on_overflow=False)

    try:
        async with websockets.connect(url, additional_headers=headers) as ws:
            logger.info(f"🎤 Language: {DEEPGRAM_LANGUAGE.upper()} | Model: {DEEPGRAM_MODEL.upper()}")
            logger.info("Connected to Deepgram WebSocket")
            logger.info("Press Stop to end")

            async def send_audio():
                try:
                    while not stop_event.is_set():
                        data = await loop.run_in_executor(None, read_audio)
                        await ws.send(data)
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.error(f"Send error: {e}")

            async def recv_transcripts():
                global full_sermon_transcript
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
                                logger.info(f"📝 {sentence}")
                                full_sermon_transcript += " " + sentence.strip()
                                _process_transcript_blob(sentence, partial_context, controller)
                        except Exception as e:
                            logger.error(f"Recv error: {e}")
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.warning(f"WebSocket closed: {e}")

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
        if stream:
            stream.stop_stream()
            stream.close()
        audio.terminate()


# ── SARVAM STREAMING ──────────────────────────────────────────────────────────
async def stream_audio_sarvam(controller):
    global full_sermon_transcript
    import base64
    from sarvamai import AsyncSarvamAI
    import pyaudio

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
                    model="saaras:v3", mode="transcribe",
                    language_code=SARVAM_LANGUAGE, sample_rate=RATE,
                    high_vad_sensitivity=True, vad_signals=False,
                    input_audio_codec="pcm_s16le",
                ) as ws:
                    logger.info(f"Sarvam AI connected — {SARVAM_LANGUAGE} saaras:v3")

                    partial_context = [""]

                    async def send_audio():
                        try:
                            while not stop_event.is_set():  # type: ignore
                                pcm_data = await loop.run_in_executor(None, read_chunk_blocking)  # type: ignore
                                await ws.transcribe(audio=base64.b64encode(pcm_data).decode("utf-8"))  # type: ignore
                        except asyncio.CancelledError:
                            pass
                        except Exception as e:
                            logger.error(f"Sarvam send error: {e}")

                    async def keepalive():
                        try:
                            while not stop_event.is_set():  # type: ignore
                                await asyncio.sleep(25)
                                if not stop_event.is_set():  # type: ignore
                                    silence = b'\x00' * CHUNK * 2
                                    await ws.transcribe(audio=base64.b64encode(silence).decode("utf-8"))  # type: ignore
                        except Exception:
                            pass

                    async def recv_transcripts():
                        global full_sermon_transcript
                        try:
                            async for message in ws:
                                try:
                                    if isinstance(message, dict):
                                        sentence = message.get("transcript", message.get("text", ""))
                                    else:
                                        sentence = (
                                            getattr(message.data, "transcript", "")
                                            if hasattr(message, "data")
                                            else getattr(message, "transcript",
                                                         getattr(message, "text", ""))
                                        )
                                    sentence = str(sentence).strip()
                                    if sentence and sentence != "None":
                                        logger.info(f"📝 {sentence}")
                                        full_sermon_transcript += " " + sentence.strip()
                                        _process_transcript_blob(sentence, partial_context, controller)
                                except Exception as e:
                                    logger.error(f"Sarvam parse error: {e}")
                        except asyncio.CancelledError:
                            pass
                        except Exception as e:
                            if not stop_event.is_set():
                                logger.warning(f"Sarvam session ended (will reconnect): {e}")

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
        if stream:
            stream.stop_stream()
            stream.close()
        audio.terminate()


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

    logger.info("=" * 60)
    logger.info("🚀 VerseView Live Started")
    logger.info(f"   Engine: {'Sarvam AI (Malayalam)' if USE_SARVAM else 'Deepgram'}")
    logger.info("=" * 60)

    try:
        points_task = asyncio.create_task(live_points_loop())

        if USE_SARVAM:
            await stream_audio_sarvam(_controller)
        else:
            await stream_audio(_controller)
    finally:
        points_task.cancel()
        if panic_listener:
            panic_listener.stop()
        _controller.cleanup()
        _controller = None
        logger.info(f"📊 LLM calls: {LLM_CALL_COUNT}")
        logger.info("Shutdown complete")
        _discord_live_log.stop()


if __name__ == "__main__":
    asyncio.run(main())
