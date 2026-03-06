# -*- coding: utf-8 -*-
import asyncio
import sys
import time
import re
import logging
import pyaudio
import requests
import certifi
import threading
import openai
from pynput import keyboard as pynput_kb

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from parse_reference_eng   import parse_references as parse_eng, normalize_numbers_only as norm_eng
from parse_reference_hindi import parse_references as parse_hindi, normalize_numbers_only as norm_hindi
from parse_reference_ml    import parse_references as parse_ml, normalize_numbers_only as norm_ml
from bible_fetcher         import fetch_verse as multi_fetch

# ── LOGGING ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s  %(message)s",
    handlers=[
        logging.FileHandler("verseview.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ── DEFAULTS ──
USE_XPATH        = sys.platform == "darwin"
USE_SARVAM       = False
DEEPGRAM_LANGUAGE = "en"
DEEPGRAM_MODEL    = "nova-2"
SARVAM_LANGUAGE   = "ml-IN"
PRIMARY_PARSER    = parse_eng
MIC_INDEX         = 1
RATE              = 16000
CHUNK             = 4096
REMOTE_URL        = "http://localhost:50010/control.html"
DEDUP_WINDOW      = 60
COOLDOWN          = 3.0
LLM_ENABLED       = True
LLM_CALL_COUNT    = 0
BIBLE_TRANSLATION = "web"
DEEPGRAM_API_KEY  = ""
GROQ_API_KEY      = ""
DISCORD_WEBHOOK_URL = ""
SARVAM_API_KEY    = ""

CONFIDENCE_THRESHOLD = 0.75
REQUIRE_MANUAL_CONFIRM = True
CONFIRM_CALLBACK       = None
REQUIRE_VERIFY       = True
PANIC_KEY            = "esc"

# ── SMART AMEN CONFIG ──
SMART_AMEN_ENABLED   = True
SMART_AMEN_KEYWORDS  = [
    "let us pray",
    "let's pray",
    "please be seated",
    "bow our heads",
    "thank you jesus"
]

llm_client = openai.OpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY)

# ── GLOBALS & SERMON BUFFER ──
stop_event   = None
engine_loop  = None
_controller  = None

full_sermon_transcript = ""
verses_cited           = []

# ── STOP & PANIC LOGIC ──
def request_stop():
    """ Called ONLY by the GUI's Stop Button """
    global stop_event, engine_loop
    if engine_loop and stop_event:
        engine_loop.call_soon_threadsafe(stop_event.set)
    logger.info("🛑 Stop requested from GUI.")

def trigger_panic():
    """ Called ONLY by the keyboard Hotkey """
    global _controller
    if _controller:
        _controller.close_presentation()

# ── SMART AMEN LOGIC ──
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

# ── SERMON SUMMARY GENERATOR ──
def generate_sermon_summary():
    global full_sermon_transcript, verses_cited, LLM_ENABLED, llm_client
    
    if not LLM_ENABLED or not GROQ_API_KEY:
        return "⚠️ LLM Fallback is disabled or missing Groq API Key. Required to generate summaries."
        
    if len(full_sermon_transcript.strip()) < 100:
        return "⚠️ Transcript is too short to generate a meaningful summary."

    prompt = (
        "You are an expert sermon note-taker. Read the following sermon transcript "
        "and generate structured sermon notes using the exact Markdown format below. "
        "IMPORTANT: If the transcript contains any other languages (such as Malayalam, Hindi, or others), "
        "you must translate those portions and write the final output strictly in English.\n\n"
        "Extract the information from the transcript as best as you can.\n\n"
        "---FORMAT TEMPLATE START---\n"
        "## 📅 [Extract Date if present, or write 'Date'] | [Sermon Series Name if mentioned]\n"
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
        "### 🏃‍♂️ The 'So What?' (Application)\n"
        "1. **Immediate Step:** [A practical action step the listener can do this week]\n"
        "2. **Prayer Focus:** [A short prayer prompt related to the message]\n"
        "---FORMAT TEMPLATE END---\n\n"
        f"Transcript:\n{full_sermon_transcript}\n"
    )

    try:
        logger.info("⏳ Generating Sermon Cliff Notes via AI... (This may take a moment)")
        response = llm_client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[{"role": "user", "content": prompt}]
        )
        summary = response.choices[0].message.content.strip()
        
        # Append verses
        verse_str = "\n".join([f"- {v}" for v in verses_cited])
        if verse_str:
            summary += "\n\n### Verses Cited:\n" + verse_str
            
        logger.info("✅ Sermon Summary generated!")
        return summary
    except Exception as e:
        logger.error(f"❌ Failed to generate summary: {e}")
        return f"Error generating summary: {e}"

def clear_sermon_buffer():
    global full_sermon_transcript, verses_cited
    full_sermon_transcript = ""
    verses_cited = []
    logger.info("🗑️ Sermon memory has been manually cleared.")

# ── CONFIGURE ──
def configure(
    language="en", mic_index=1, rate=16000, chunk=4096,
    remote_url="http://localhost:50010/control.html",
    dedup_window=60, cooldown=3.0, llm_enabled=True,
    bible_translation="kjv", deepgram_api_key="",
    groq_api_key="", sarvam_api_key="",
    discord_webhook_url="", confidence=0.75, manual_confirm=True, confirm_callback=None, verify=True, panic_key="esc", smart_amen=True
):
    global DEEPGRAM_API_KEY, GROQ_API_KEY, SARVAM_API_KEY, DISCORD_WEBHOOK_URL
    global USE_SARVAM, DEEPGRAM_LANGUAGE, DEEPGRAM_MODEL, SARVAM_LANGUAGE
    global PRIMARY_PARSER, MIC_INDEX, RATE, CHUNK, REMOTE_URL
    global DEDUP_WINDOW, COOLDOWN, LLM_ENABLED, BIBLE_TRANSLATION, USE_XPATH, llm_client
    global CONFIDENCE_THRESHOLD, REQUIRE_MANUAL_CONFIRM, CONFIRM_CALLBACK, REQUIRE_VERIFY, PANIC_KEY, SMART_AMEN_ENABLED
    global full_sermon_transcript, verses_cited

    # NOTE: Sermon buffer is intentionally NOT reset here so memory persists across stops/starts!

    DEEPGRAM_API_KEY    = deepgram_api_key
    GROQ_API_KEY        = groq_api_key
    SARVAM_API_KEY      = sarvam_api_key
    DISCORD_WEBHOOK_URL = discord_webhook_url
    llm_client = openai.OpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY)

    USE_XPATH     = sys.platform == "darwin"
    MIC_INDEX     = mic_index
    RATE          = rate
    CHUNK         = chunk
    REMOTE_URL    = remote_url
    DEDUP_WINDOW  = dedup_window
    COOLDOWN      = cooldown
    LLM_ENABLED   = llm_enabled
    BIBLE_TRANSLATION = bible_translation
    
    CONFIDENCE_THRESHOLD   = confidence
    REQUIRE_MANUAL_CONFIRM = manual_confirm
    CONFIRM_CALLBACK       = confirm_callback
    REQUIRE_VERIFY         = verify
    PANIC_KEY              = panic_key
    SMART_AMEN_ENABLED     = smart_amen

    global normalize_numbers_only
    if language == "en":
        USE_SARVAM        = False
        DEEPGRAM_LANGUAGE = "en"
        DEEPGRAM_MODEL    = "nova-2"
        PRIMARY_PARSER    = parse_eng
        normalize_numbers_only = norm_eng
        
    elif language == "hi":
        USE_SARVAM        = False
        DEEPGRAM_LANGUAGE = "hi"
        DEEPGRAM_MODEL    = "nova-3"
        PRIMARY_PARSER    = parse_hindi
        normalize_numbers_only = norm_hindi
        
    elif language == "ml":
        USE_SARVAM        = True
        SARVAM_LANGUAGE   = "ml-IN"
        PRIMARY_PARSER    = parse_ml
        normalize_numbers_only = norm_ml
        
    else:
        USE_SARVAM        = False
        DEEPGRAM_LANGUAGE = "multi"
        DEEPGRAM_MODEL    = "nova-2"
        PRIMARY_PARSER    = parse_eng
        normalize_numbers_only = norm_eng

# ── CONTEXT TRACKING ──
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

# ── VERSE RANGE QUEUE ──
verse_queue      = []
verse_queue_lock = threading.Lock()

RANGE_RE = re.compile(r'(?P<start>\d+)\s*(?:through|thru|to|and|ending\s+at|-|–)\s*(?P<end>\d+)', re.IGNORECASE | re.VERBOSE)

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

# ── BIBLE FETCH ──
def fetch_verse_text(ref: str) -> str | None:
    text = multi_fetch(ref, BIBLE_TRANSLATION)
    if text:
        return text
    logger.warning(f"All APIs failed for {ref}")
    return None

# ── ONWARDS MODE ──
onwards_active     = False
onwards_book       = None
onwards_chapter    = None
onwards_verse      = None
onwards_timer      = None
onwards_target_ref = None
onwards_trigger    = None

def _stop_onwards():
    global onwards_active, onwards_timer, onwards_target_ref, onwards_trigger
    onwards_active = False
    if onwards_timer:
        onwards_timer.cancel()
    onwards_timer = None
    onwards_target_ref = None
    onwards_trigger = None
    logger.info("⏹️  ONWARDS mode stopped")

def _reset_onwards_timer():
    global onwards_timer
    if onwards_timer:
        onwards_timer.cancel()
    onwards_timer = threading.Timer(60.0, _stop_onwards)
    onwards_timer.daemon = True
    onwards_timer.start()

def _fetch_next_onwards():
    global onwards_target_ref, onwards_trigger
    if not onwards_active:
        return
    next_v = onwards_verse + 1
    ref = f"{onwards_book} {onwards_chapter}:{next_v}"
    text = fetch_verse_text(ref)
    
    if text:
        words = re.findall(r'[a-z]+', text.lower())[:6]
        onwards_trigger = " ".join(words)
        onwards_target_ref = ref
        logger.info(f"⏭️  ONWARDS LISTENING FOR: {ref} | Trigger: '{onwards_trigger}'")
    else:
        logger.warning(f"⚠️  ONWARDS couldn't fetch {ref} - stopping onwards mode.")
        _stop_onwards()

def _start_onwards(book, chapter, verse):
    global onwards_active, onwards_book, onwards_chapter, onwards_verse
    _stop_onwards()
    onwards_active  = True
    onwards_book    = book
    onwards_chapter = chapter
    onwards_verse   = int(verse)
    _reset_onwards_timer()
    logger.info(f"▶️  ONWARDS mode started from {book} {chapter}:{verse}")
    threading.Thread(target=_fetch_next_onwards, daemon=True).start()

def _check_onwards_advance(text, controller) -> bool:
    global onwards_verse
    if not onwards_active or not onwards_target_ref or not onwards_trigger:
        return False
        
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
            ref = f"{book} {chapter}:{v}"
            text = fetch_verse_text(ref)
            if text:
                words = re.findall(r'[a-z]+', text.lower())[:6]
                trigger = " ".join(words)
                with verse_queue_lock:
                    verse_queue.append((ref, trigger))
                logger.info(f"📚 Queued: {ref} | Trigger: '{trigger}'")

    threading.Thread(target=fetch_all, daemon=True).start()
    logger.info(f"📖 Range queued: {book} {chapter}:{start_verse} → {end_verse}")

def check_verse_queue(transcript, controller) -> bool:
    with verse_queue_lock:
        if not verse_queue:
            return False
        next_ref, trigger = verse_queue[0]
        transcript_words  = set(re.findall(r'[a-z]+', transcript.lower()))
        check_words       = trigger.split()[:4]
        matches           = sum(1 for w in check_words if w in transcript_words)
        threshold         = min(2, len(check_words))
        if matches >= threshold:
            verse_queue.pop(0)
        else:
            return False

    logger.info(f"🎯 AUTO-ADVANCE: {next_ref} (heard '{trigger[:30]}')")
    controller.send_verse(next_ref, bypass_cooldown=True)
    return True

def check_and_queue_range(text, base_ref, controller):
    if ":" not in base_ref:
        return
        
    num_norm = normalize_numbers_only(text)
    range_m = RANGE_RE.search(num_norm)
    if not range_m:
        return
        
    try:
        end_v = int(range_m.group("end"))
        parts = base_ref.split()
        book = " ".join(parts[:-1])
        chap_str, startv_str = parts[-1].split(":")
        start_v = int(startv_str)
        
        if end_v > start_v and end_v <= start_v + 30:
            queue_verse_range(book, chap_str, start_v, end_v, controller)
    except Exception:
        return

# ── DISCORD ──
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

# ── LLM FALLBACK ──
def extract_verse_with_llm(text):
    global LLM_CALL_COUNT
    
    context_hint = ""
    if current_book and current_chapter:
        context_hint = f"\nContext: The speaker is currently reading from {current_book} chapter {current_chapter}."

    try:
        LLM_CALL_COUNT += 1
        response = llm_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{
                "role": "user",
                "content": (
                    f"Extract the Bible verse reference from this text. "
                    f"Return ONLY in format Book Chapter:Verse (e.g., John 3:16). "
                    f"If no verse found, return exactly NONE.{context_hint}\nText: {text}"
                )
            }]
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

# ── VERSE CONTROLLER ──
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
                options=options
            )
            self.driver.get(REMOTE_URL)
            wait = WebDriverWait(self.driver, 15)
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
                except:
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
            return False

    def close_presentation(self):
        """ Clears the screen via the VerseView X button """
        if not self.driver: return
        try:
            close_btn = self.driver.find_element(By.ID, "iconClose")
            close_btn.click()
            logger.info("🚫 Presentation cleared off the screen!")
        except Exception as e:
            logger.debug(f"Could not click close button (maybe already closed): {e}")

    def send_verse(self, ref, bypass_cooldown=False, confidence=1.0):
        global current_book, current_chapter, current_verse, verses_cited
        now = time.time()

        # ── MANUAL CONFIRMATION LOGIC ──
        if confidence < CONFIDENCE_THRESHOLD and not bypass_cooldown:
            if REQUIRE_MANUAL_CONFIRM and CONFIRM_CALLBACK:
                def _ask_thread():
                    logger.info(f"🤔 Holding for manual confirmation: {ref} (Confidence: {int(confidence*100)}%)")
                    if CONFIRM_CALLBACK(ref, confidence):
                        logger.info(f"✅ User manually approved: {ref}")
                        self.send_verse(ref, bypass_cooldown=True, confidence=1.0)
                    else:
                        logger.info(f"❌ User rejected: {ref}")
                threading.Thread(target=_ask_thread, daemon=True).start()
                return False
            else:
                logger.warning(f"⚠️ Blocked: {ref} (Confidence {int(confidence*100)}% < Threshold {int(CONFIDENCE_THRESHOLD*100)}%)")
                return False

        # ── VERIFICATION LOGIC (Hear Twice) ──
        if REQUIRE_VERIFY and not bypass_cooldown:
            if self.pending_verse == ref:
                self.match_count += 1
            else:
                self.pending_verse = ref
                self.match_count = 1
                logger.info(f"⏳ Verification pending for: {ref} (Heard once...)")
                return False
                
            if self.match_count < 2:
                return False
                
            self.pending_verse = None
            self.match_count = 0

        # ── STANDARD COOLDOWNS ──
        if ref in self.history and (now - self.history[ref]) < DEDUP_WINDOW:
            logger.debug(f"Skipped duplicate: {ref}")
            return False

        if not bypass_cooldown and self.last_sent and (now - self.last_time) < COOLDOWN:
            logger.debug(f"Cooldown active: {ref}")
            return False

        # ── SEND TO VERSEVIEW ──
        try:
            if not self.driver:
                if not self.connect():
                    return False

            self.driver.execute_script("arguments[0].value = arguments[1];", self.box, ref)
            self.driver.execute_script("arguments[0].click();", self.btn)
            logger.info(f"✅ PRESENTED: {ref}")
            
            # --- Store presented verse for the Sermon Notes! ---
            if ref not in verses_cited:
                verses_cited.append(ref)

            send_to_discord(ref)

            parts = ref.split()
            if len(parts) >= 2:
                if ":" in parts[-1]:
                    current_book                   = " ".join(parts[:-1])
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
            except:
                pass
            self.driver = None
            return False

    def cleanup(self):
        if self.driver:
            try:
                self.driver.quit()
                logger.info("VerseView connection closed")
            except:
                pass

# ── HYBRID VERSE DETECTOR ──
ONWARDS_KEYWORDS = ["onwards", "onward", "and following", "and beyond", "and after"]

def detect_verse_hybrid(text, controller, confidence=1.0) -> bool:
    global current_book, current_chapter, current_verse

    if not text or len(text.strip()) < 3:
        return False

    # --- PHONETIC FIXES (Catch common speech-to-text errors before parsing) ---
    fixes = {
        r"\b(?:sam's|sams|sam)\b": "psalms",
        r"\bnayan\b": "nine"
    }
    for pattern, replacement in fixes.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    # --------------------------------------------------------------------------

    def trigger_onwards_if_needed(ref_string, original_text):
        if any(kw in original_text.lower() for kw in ONWARDS_KEYWORDS):
            parts = ref_string.split()
            if ":" in parts[-1]:
                ch, vs = parts[-1].split(":")
                bk = " ".join(parts[:-1])
                _start_onwards(bk, ch, vs)

    try:
        if check_verse_queue(text, controller):
            return True
            
        if _check_onwards_advance(text, controller):
            return True
        
        num_norm = normalize_numbers_only(text)
        num_norm = re.sub(
            r'\b(20|30|40|50|60|70|80|90)\s+([1-9])\b', 
            lambda m: str(int(m.group(1)) + int(m.group(2))), 
            num_norm
        )

        # Layer 1 — parser
        refs = PRIMARY_PARSER(text)
        if refs:
            verse = refs[0]
            
            is_blocked = False
            if ":" not in verse:
                chap_num = verse.split()[-1]
                blockers = ["days", "weeks", "months", "years", "minutes", "hours", "people", "men", "women", "points", "dollars"]
                if any(re.search(rf'\b{chap_num}\s+{b}\b', num_norm) for b in blockers):
                    logger.info(f"🚫 BLOCKED Layer 1 False Positive: {verse} (Time/People phrase)")
                    is_blocked = True
            
            if not is_blocked:
                logger.info(f"🔍 PARSER: {verse} ({int(confidence*100)}% Acc)")
                controller.send_verse(verse, confidence=confidence)
                
                trigger_onwards_if_needed(verse, text)
                
                if ":" in verse:
                    check_and_queue_range(text, verse, controller)
                return True

        # Layer 2 — contextual (number only, same book/chapter)
        m = re.search(r'\b(\d+)\b', num_norm)
        if m and current_book and current_chapter:
            candidate = m.group(1)
            text_lower = num_norm.lower()
            
            is_valid = False
            
            if len(text.split()) <= 2:
                is_valid = True
            elif re.search(r'\b(?:verse|verses|v|vs)\s+' + candidate + r'\b', text_lower):
                is_valid = True
            elif any(kw in text_lower for kw in ["വാക്യം", "വചനം", "വചന", "वचन", "पद"]):
                is_valid = True
                
            if is_valid:
                ref = f"{current_book} {current_chapter}:{candidate}"
                logger.info(f"🔍 CONTEXTUAL: {ref} ({int(confidence*100)}% Acc)")
                controller.send_verse(ref, confidence=confidence)
                
                trigger_onwards_if_needed(ref, text)
                check_and_queue_range(num_norm, ref, controller)
                return True

       # Layer 3 — Hindi contextual
        m_hi = re.search(r'([\u0966-\u096F]+)', text)
        if m_hi and current_book and current_chapter:
            ref = f"{current_book} {current_chapter}:{m_hi.group(1)}"
            logger.info(f"🔍 HINDI CTX: {ref} ({int(confidence*100)}% Acc)")
            controller.send_verse(ref, confidence=confidence)
            trigger_onwards_if_needed(ref, text)
            return True

        # Layer 4 — Malayalam contextual
        m_ml = re.search(r'([\u0D66-\u0D6F]+)', text)
        if m_ml and current_book and current_chapter:
            ref = f"{current_book} {current_chapter}:{m_ml.group(1)}"
            logger.info(f"🔍 MALAYALAM CTX: {ref} ({int(confidence*100)}% Acc)")
            controller.send_verse(ref, confidence=confidence)
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
                        controller.send_verse(ref, confidence=confidence)
                        trigger_onwards_if_needed(ref, text)
                        return True
                except ValueError:
                    pass

        # Layer 6 — range without explicit verse
        if current_book and current_chapter:
            range_m = RANGE_RE.search(num_norm)
            if range_m:
                start_v = int(range_m.group("start"))
                end_v   = int(range_m.group("end"))
                text_after = num_norm[range_m.end():].strip()
                blockers = [
                    "bibles","dollars","days","weeks","months","years",
                    "minutes","hours","times","people","men","women",
                    "students","countries","churches","teams"
                ]
                if not any(text_after.startswith(b) for b in blockers):
                    if 1 <= start_v < end_v <= start_v + 30:
                        ref_start = f"{current_book} {current_chapter}:{start_v}"
                        logger.info(f"🔍 RANGE: {current_book} {current_chapter}:{start_v} → {end_v} ({int(confidence*100)}% Acc)")
                        controller.send_verse(ref_start, confidence=confidence)
                        queue_verse_range(current_book, current_chapter, start_v, end_v, controller)
                        trigger_onwards_if_needed(ref_start, text)
                        return True

        # Layer 8 — simple "Book chapter" pattern
        m_simple = re.search(
            r'\b((?:[1-3]\s*)?(?:' + '|'.join(BOOK_KEYWORDS[:40]) + r'))\s+(\d{1,3})\b',
            text, re.IGNORECASE
        )
        if m_simple:
            ref = f"{m_simple.group(1).strip().title()} {m_simple.group(2)}"
            logger.info(f"🔍 SIMPLE: {ref} ({int(confidence*100)}% Acc)")
            controller.send_verse(ref, confidence=confidence)
            trigger_onwards_if_needed(ref, text)
            return True

        # Layer 9 — LLM fallback
        if not LLM_ENABLED:
            return False

        text_lower  = text.lower()
        has_book    = any(kw in text_lower for kw in BOOK_KEYWORDS)
        has_number  = bool(re.search(r'\d+', text)) or any(w in text_lower for w in NUMBER_WORDS)

        if not has_book and not has_number:
            return False

        # --- LLM ANTI-SPAM (Debouncer) ---
        if len(text.split()) < 4 and not has_number:
            return False
        # ---------------------------------

        logger.info(f"📞 LLM: '{text[:80]}'")

        def llm_task():
            verse = extract_verse_with_llm(text)
            if verse:
                controller.send_verse(verse, confidence=confidence)
                trigger_onwards_if_needed(verse, text)
                check_and_queue_range(text, verse, controller)

        threading.Thread(target=llm_task, daemon=True).start()
        return True

    except Exception as e:
        logger.error(f"Parse error: {e}")
        return False

# ── DEEPGRAM STREAMING ──
async def stream_audio(controller):
    global full_sermon_transcript
    import websockets
    import json

    partial_context = ""

    audio  = pyaudio.PyAudio()
    stream = None

    try:
        mic_info = audio.get_device_info_by_index(MIC_INDEX)
        logger.info(f"Using: [{MIC_INDEX}] {mic_info['name']}")
        stream = audio.open(
            format=pyaudio.paInt16, channels=1, rate=RATE,
            input=True, input_device_index=MIC_INDEX,
            frames_per_buffer=CHUNK
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
                nonlocal partial_context
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
                                
                            confidence = alts[0].get("confidence", 1.0)
                            sentence = alts[0].get("transcript", "")
                            
                            if not sentence.strip():
                                continue

                            check_verse_queue(sentence, controller)

                            if data.get("is_final"):
                                logger.info(f"📝 {sentence}")
                                
                                # --- Add to Sermon Buffer ---
                                full_sermon_transcript += " " + sentence.strip()

                                if check_smart_amen(sentence, controller):
                                    partial_context = "" 
                                    continue

                                partial_context += " " + sentence.strip()
                                
                                # Send confidence down into the detector
                                found = detect_verse_hybrid(partial_context, controller, confidence=confidence)
                                if found:
                                    partial_context = ""
                                else:
                                    words = partial_context.split()
                                    if len(words) > 30:
                                        partial_context = " ".join(words[-15:])
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
                await ws.send(json.dumps({"type": "CloseStream"}))
            except:
                pass
    except Exception as e:
        logger.error(f"Deepgram WebSocket error: {e}")
    finally:
        if stream:
            stream.stop_stream()
            stream.close()
        audio.terminate()

# ── SARVAM STREAMING ──
async def stream_audio_sarvam(controller):
    global full_sermon_transcript
    import base64
    from sarvamai import AsyncSarvamAI

    audio  = pyaudio.PyAudio()
    stream = None

    try:
        mic_info = audio.get_device_info_by_index(MIC_INDEX)
        logger.info(f"Using: [{MIC_INDEX}] {mic_info['name']}")
        stream = audio.open(
            format=pyaudio.paInt16, channels=1, rate=RATE,
            input=True, input_device_index=MIC_INDEX,
            frames_per_buffer=CHUNK
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

    logger.info("Connecting to Sarvam AI...")
    try:
        client = AsyncSarvamAI(api_subscription_key=SARVAM_API_KEY)
        loop   = asyncio.get_event_loop()

        async with client.speech_to_text_streaming.connect(
            model="saaras:v3", 
            mode="transcribe",
            language_code=SARVAM_LANGUAGE,
            sample_rate=RATE,
            high_vad_sensitivity=False,
            vad_signals=False,
            input_audio_codec="pcm_s16le" 
        ) as ws:
            logger.info(f"Sarvam AI connected — {SARVAM_LANGUAGE} saaras:v3")

            async def send_audio():
                try:
                    while not stop_event.is_set():
                        pcm_data = await loop.run_in_executor(None, read_chunk_blocking)
                        pcm_b64 = base64.b64encode(pcm_data).decode("utf-8")
                        await ws.transcribe(audio=pcm_b64)
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.error(f"Sarvam send error: {e}")

            async def recv_transcripts():
                global full_sermon_transcript
                try:
                    async for message in ws:
                        try:
                            if isinstance(message, dict):
                                sentence = message.get("transcript", message.get("text", ""))
                            else:
                                if hasattr(message, "data"):
                                    sentence = getattr(message.data, "transcript", "")
                                else:
                                    sentence = getattr(message, "transcript", getattr(message, "text", ""))
                                
                            sentence = str(sentence).strip()
                            
                            if sentence and sentence != "None":
                                logger.info(f"📝 {sentence}")
                                
                                # --- Add to Sermon Buffer ---
                                full_sermon_transcript += " " + sentence.strip()

                                if check_smart_amen(sentence, controller):
                                    continue
                                
                                check_verse_queue(sentence, controller)
                                detect_verse_hybrid(sentence, controller, confidence=1.0)
                        except Exception as e:
                            logger.error(f"Sarvam message parsing error: {e}")
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.warning(f"Sarvam closed: {e}")

            sender   = asyncio.create_task(send_audio())
            receiver = asyncio.create_task(recv_transcripts())
            await stop_event.wait()
            sender.cancel()
            receiver.cancel()
            await asyncio.gather(sender, receiver, return_exceptions=True)
    except Exception as e:
        logger.error(f"Sarvam connection error: {e}")
    finally:
        if stream:
            stream.stop_stream()
            stream.close()
        audio.terminate()

# ── MAIN ──
async def main():
    global stop_event, engine_loop, _controller
    stop_event  = asyncio.Event()
    engine_loop = asyncio.get_event_loop()

    # ── PANIC BUTTON BINDING ──
    try:
        if PANIC_KEY:
            def on_press(key):
                try:
                    k = key.char
                except AttributeError:
                    k = key.name
                
                # If the key they pressed matches their saved setting, clear the screen!
                if k == PANIC_KEY:
                    trigger_panic()

            # Start a background thread to listen for the panic key
            panic_listener = pynput_kb.Listener(on_press=on_press)
            panic_listener.daemon = True
            panic_listener.start()
            
            logger.info(f"🚨 Panic Button active on: '{PANIC_KEY}'")
    except Exception as e:
        logger.warning(f"⚠️ Could not bind panic key: {e}")

    _controller = VerseController()
    connected  = False

    for attempt in range(1, 6):
        logger.info(f"Connection attempt {attempt}/5...")
        if _controller.connect():
            connected = True
            break
        if stop_event.is_set():
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
        if USE_SARVAM:
            await stream_audio_sarvam(_controller)
        else:
            await stream_audio(_controller)
    finally:
        _controller.cleanup()
        _controller = None
        logger.info(f"📊 LLM calls: {LLM_CALL_COUNT}")
        logger.info("Shutdown complete")

if __name__ == "__main__":
    asyncio.run(main())
