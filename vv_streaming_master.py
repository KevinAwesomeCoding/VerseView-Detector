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
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from parse_reference_eng import (
    parse_references as parse_eng,
    normalize_text as normalize_eng,
    normalize_numbers_only
)
from parse_reference_hindi import parse_references as parse_hindi
from parse_reference_ml import parse_references as parse_ml
from bible_fetcher import fetch_verse as _multi_fetch

# ========== LOGGING ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('verseview.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ========== DEFAULTS ==========
USE_XPATH         = sys.platform == "darwin"
USE_SARVAM        = False
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
BIBLE_TRANSLATION = "kjv"

DEEPGRAM_API_KEY    = ""
OPENROUTER_API_KEY  = ""
DISCORD_WEBHOOK_URL = ""
SARVAM_API_KEY      = ""

llm_client = openai.OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY
)

# ========== STOP MECHANISM ==========
_stop_event:  asyncio.Event | None = None
_engine_loop: asyncio.AbstractEventLoop | None = None

def request_stop():
    global _stop_event, _engine_loop
    if _engine_loop and _stop_event:
        _engine_loop.call_soon_threadsafe(_stop_event.set)

# ========== CONFIGURE ==========
def configure(
    language            = "en",
    mic_index           = 1,
    rate                = 16000,
    chunk               = 4096,
    remote_url          = "http://localhost:50010/control.html",
    dedup_window        = 60,
    cooldown            = 3.0,
    llm_enabled         = True,
    bible_translation   = "kjv",
    deepgram_api_key    = "",
    openrouter_api_key  = "",
    sarvam_api_key      = "",
    discord_webhook_url = "",
):
    global DEEPGRAM_API_KEY, OPENROUTER_API_KEY, SARVAM_API_KEY, DISCORD_WEBHOOK_URL
    global USE_SARVAM, DEEPGRAM_LANGUAGE, DEEPGRAM_MODEL, SARVAM_LANGUAGE
    global PRIMARY_PARSER, MIC_INDEX, RATE, CHUNK, REMOTE_URL
    global DEDUP_WINDOW, COOLDOWN, LLM_ENABLED, BIBLE_TRANSLATION, USE_XPATH
    global llm_client

    DEEPGRAM_API_KEY    = deepgram_api_key
    OPENROUTER_API_KEY  = openrouter_api_key
    SARVAM_API_KEY      = sarvam_api_key
    DISCORD_WEBHOOK_URL = discord_webhook_url

    llm_client = openai.OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY
    )

    USE_XPATH         = sys.platform == "darwin"
    MIC_INDEX         = mic_index
    RATE              = rate
    CHUNK             = chunk
    REMOTE_URL        = remote_url
    DEDUP_WINDOW      = dedup_window
    COOLDOWN          = cooldown
    LLM_ENABLED       = llm_enabled
    BIBLE_TRANSLATION = bible_translation

    if language == "en":
        USE_SARVAM        = False
        DEEPGRAM_LANGUAGE = "en"
        DEEPGRAM_MODEL    = "nova-2"
        PRIMARY_PARSER    = parse_eng
    elif language == "hi":
        USE_SARVAM        = False
        DEEPGRAM_LANGUAGE = "hi"
        DEEPGRAM_MODEL    = "nova-3"
        PRIMARY_PARSER    = parse_hindi
    elif language == "ml":
        USE_SARVAM        = True
        SARVAM_LANGUAGE   = "ml-IN"
        PRIMARY_PARSER    = parse_ml
    else:
        USE_SARVAM        = False
        DEEPGRAM_LANGUAGE = "multi"
        DEEPGRAM_MODEL    = "nova-2"
        PRIMARY_PARSER    = parse_eng

# ========== CONTEXT TRACKING ==========
current_book    = None
current_chapter = None
current_verse   = None

def get_context() -> dict:
    return {
        "book":    current_book    or "",
        "chapter": current_chapter or "",
        "verse":   current_verse   or "",
    }

def set_context(book: str, chapter: str, verse: str):
    global current_book, current_chapter, current_verse
    current_book    = book.strip()    or None
    current_chapter = chapter.strip() or None
    current_verse   = verse.strip()   or None
    logger.info(f"📌 Context manually set: {current_book} {current_chapter}:{current_verse}")

# ========== VERSE RANGE QUEUE ==========
verse_queue      = []
verse_queue_lock = threading.Lock()

RANGE_RE = re.compile(
    r'(?P<start>\d+)\s+(?:through|thru|to|and)\s+(?P<end>\d+)',
    re.IGNORECASE
)

BOOK_KEYWORDS = [
    "genesis","exodus","leviticus","numbers","deuteronomy",
    "joshua","judges","ruth","samuel","kings","chronicles",
    "ezra","nehemiah","esther","job","psalm","psalms",
    "proverbs","ecclesiastes","isaiah","jeremiah",
    "lamentations","ezekiel","daniel","hosea","joel",
    "amos","obadiah","jonah","micah","nahum","habakkuk",
    "zephaniah","haggai","zechariah","malachi",
    "matthew","mark","luke","john","acts","romans",
    "corinthians","galatians","ephesians","philippians",
    "colossians","thessalonians","timothy","titus",
    "philemon","hebrews","james","peter","jude","revelation",
    "मत्ती","मरकुस","लूका","यूहन्ना","रोमियों",
    "उत्पत्ति","भजन","यशायाह","प्रकाशितवाक्य",
    "इफिसियों","गलातियों","फिलिप्पियों","कुलुस्सियों",
    "മത്തായി","മർക്കോസ്","ലൂക്കോസ്","യോഹന്നാൻ",
    "റോമർ","ഉല്പത്തി","സങ്കീർത്തനങ്ങൾ","യെശയ്യാവ്",
    "വെളിപാടു","എഫെസ്യർ","ഗലാത്യർ","ദാനിയേൽ",
]

NUMBER_WORDS = [
    "one","two","three","four","five","six","seven","eight",
    "nine","ten","eleven","twelve","thirteen","fourteen","fifteen",
    "sixteen","seventeen","eighteen","nineteen","twenty","thirty",
    "forty","fifty","sixty","seventy","eighty","ninety","hundred"
]

# ========== BIBLE FETCH ==========
def fetch_verse_text(ref: str) -> str | None:
    text = _multi_fetch(ref, BIBLE_TRANSLATION)
    if text:
        return text
    logger.warning(f"⚠️ All APIs failed for {ref}")
    return None

def queue_verse_range(book, chapter, start_verse, end_verse, controller):
    with verse_queue_lock:
        verse_queue.clear()

    def _fetch_all():
        for v in range(start_verse + 1, end_verse + 1):
            ref  = f"{book} {chapter}:{v}"
            text = fetch_verse_text(ref)
            if text:
                words   = re.findall(r'[a-z]+', text.lower())[:6]
                trigger = ' '.join(words)
                with verse_queue_lock:
                    verse_queue.append((ref, trigger))
                logger.info(f"📚 Queued: {ref} | Trigger: '{trigger}'")
            else:
                logger.warning(f"⚠️ Could not fetch {ref}")

    threading.Thread(target=_fetch_all, daemon=True).start()
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
    controller.send_verse(next_ref)
    return True


def _check_and_queue_range(text, base_ref, controller):
    num_norm = normalize_numbers_only(text)
    range_m  = RANGE_RE.search(num_norm)
    if not range_m:
        return
    end_v  = int(range_m.group('end'))
    parts  = base_ref.split()
    if ':' not in parts[-1]:
        return
    book                  = ' '.join(parts[:-1])
    chap_str, start_v_str = parts[-1].split(':')
    try:
        start_v = int(start_v_str)
    except ValueError:
        return
    if end_v > start_v and end_v <= start_v + 30:
        queue_verse_range(book, chap_str, start_v, end_v, controller)

# ========== DISCORD ==========
def send_to_discord(verse: str):
    def _do_send(payload):
        try:
            r = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5, verify=certifi.where())
            if r.status_code == 204:
                logger.info("📩 Sent to Discord")
            else:
                logger.warning(f"⚠️ Discord error: {r.status_code}")
        except Exception as e:
            logger.error(f"⚠️ Discord failed: {e}")

    threading.Thread(target=_do_send, args=({"content": f"📖 Verse Detected: {verse}"},), daemon=True).start()
    lower = verse.lower().replace(" ", "")
    if "6:7" in lower or ":67" in lower or re.search(r"\b67\b", lower):
        threading.Thread(target=_do_send, args=({"content": "SIXX SEVENNN :sixseven:"},), daemon=True).start()

# ========== LLM FALLBACK ==========
def extract_verse_with_llm(text):
    global LLM_CALL_COUNT
    try:
        LLM_CALL_COUNT += 1
        response = llm_client.chat.completions.create(
            model="openrouter/auto",
            messages=[{
                "role": "user",
                "content": f"""Extract the Bible verse reference from this text.
Return ONLY in format "Book Chapter:Verse" (e.g., "John 3:16").
If no verse found, return exactly "NONE".
Text: {text}
Reference:"""
            }]
        )
        verse = response.choices[0].message.content.strip()
        if verse == "NONE":
            return None
        if re.match(r'^[123]?\s*[A-Za-z\s]+\s+\d{1,3}(:\d{1,3})?(-\d{1,3})?$', verse):
            logger.info(f"🤖 LLM extracted: {verse}")
            return verse
        return None
    except Exception as e:
        logger.error(f"❌ LLM error: {e}")
        return None

# ========== VERSEVIEW CONTROLLER ==========
class VerseController:
    def __init__(self):
        self.driver    = None
        self.box       = None
        self.btn       = None
        self.last_sent = None
        self.last_time = 0
        self.history   = {}

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
            wait     = WebDriverWait(self.driver, 15)
            self.box = wait.until(EC.presence_of_element_located((By.ID, "remote_bibleRefID")))

            btn       = None
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
                    logger.info(f"✅ Found PRESENT button: {selector}")
                    break
                except:
                    continue

            if not btn:
                all_btns = self.driver.find_elements(By.TAG_NAME, "button")
                logger.error("❌ Could not find PRESENT button.")
                for b in all_btns:
                    logger.error(f"   id='{b.get_attribute('id')}' text='{b.text}'")
                return False

            self.btn = btn
            logger.info("Connected to VerseView (headless)")
            return True
        except Exception as e:
            logger.error(f"VerseView connection failed: {e}")
            return False

    def send_verse(self, ref):
        global current_book, current_chapter, current_verse
        now = time.time()

        if ref in self.history and (now - self.history[ref]) < DEDUP_WINDOW:
            logger.debug(f"Skipped duplicate: {ref}")
            return False

        if self.last_sent and (now - self.last_time) < COOLDOWN:
            logger.debug(f"Cooldown active: {ref}")
            return False

        try:
            if not self.driver:
                if not self.connect():
                    return False

            self.driver.execute_script("arguments[0].value = arguments[1];", self.box, ref)
            self.driver.execute_script("arguments[0].click();", self.btn)
            logger.info(f"✅ PRESENTED: {ref}")

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

# ========== HYBRID VERSE DETECTOR ==========
def detect_verse_hybrid(text, controller) -> bool:
    global current_book, current_chapter, current_verse
    if not text or len(text.strip()) < 3:
        return False
    try:
        if check_verse_queue(text, controller):
            return True

        refs = PRIMARY_PARSER(text)
        if refs:
            verse = refs[0]
            logger.info(f"🔍 PARSER: {verse}")
            controller.send_verse(verse)
            _check_and_queue_range(text, verse, controller)
            return True

        num_norm = normalize_numbers_only(text)

        m = re.search(r"\bverses?\s+(\d+)(?!\s*verses?)\b", num_norm, re.IGNORECASE)
        if m and current_book and current_chapter:
            ref = f"{current_book} {current_chapter}:{m.group(1)}"
            logger.info(f"🔍 CONTEXTUAL: {ref}")
            controller.send_verse(ref)
            _check_and_queue_range(num_norm, ref, controller)
            return True

        m_hi = re.search(r"वचन\s+(\d+)", text)
        if m_hi and current_book and current_chapter:
            ref = f"{current_book} {current_chapter}:{m_hi.group(1)}"
            logger.info(f"🔍 HINDI CTX: {ref}")
            controller.send_verse(ref)
            return True

        m_ml = re.search(r"വാക്യം\s+(\d+)", text)
        if m_ml and current_book and current_chapter:
            ref = f"{current_book} {current_chapter}:{m_ml.group(1)}"
            logger.info(f"🔍 MALAYALAM CTX: {ref}")
            controller.send_verse(ref)
            return True

        if current_book and current_chapter and current_verse:
            m_num = re.search(r"\b(\d{1,3})\b", text)
            if m_num:
                candidate = m_num.group(1)
                try:
                    if int(candidate) == int(current_verse) + 1:
                        ref = f"{current_book} {current_chapter}:{candidate}"
                        logger.info(f"🔍 SEQUENTIAL: {ref}")
                        controller.send_verse(ref)
                        return True
                except ValueError:
                    pass

        if current_book and current_chapter:
            range_m = RANGE_RE.search(num_norm)
            if range_m:
                start_v    = int(range_m.group('start'))
                end_v      = int(range_m.group('end'))
                text_after = num_norm[range_m.end():].strip()
                blockers   = ["bibles","dollars","days","weeks","months","years",
                              "minutes","hours","times","people","men","women",
                              "students","countries","churches","teams"]
                if not any(text_after.startswith(b) for b in blockers):
                    if 1 <= start_v < end_v <= start_v + 30:
                        ref_start = f"{current_book} {current_chapter}:{start_v}"
                        logger.info(f"🔍 RANGE: {ref_start} → {end_v}")
                        controller.send_verse(ref_start)
                        queue_verse_range(current_book, current_chapter, start_v, end_v, controller)
                        return True

        m_simple = re.search(
            r'\b((?:[123]\s+)?(?:' + '|'.join(BOOK_KEYWORDS[:40]) + r'))\s+(\d{1,3})\b',
            text, re.IGNORECASE
        )
        if m_simple:
            ref = f"{m_simple.group(1).strip().title()} {m_simple.group(2)}"
            logger.info(f"🔍 SIMPLE: {ref}")
            controller.send_verse(ref)
            return True

        if not LLM_ENABLED:
            return False

        text_lower = text.lower()
        has_book   = any(kw in text_lower or kw in text for kw in BOOK_KEYWORDS)
        has_number = bool(re.search(r'\b\d+\b', text)) or any(w in text_lower for w in NUMBER_WORDS)
        if not (has_book and has_number):
            return False

        logger.info(f"📞 LLM: '{text[:80]}'")

        def llm_task():
            verse = extract_verse_with_llm(text)
            if verse:
                controller.send_verse(verse)
                _check_and_queue_range(text, verse, controller)

        threading.Thread(target=llm_task, daemon=True).start()
        return True

    except Exception as e:
        logger.error(f"Parse error: {e}")
        return False

# ========== DEEPGRAM STREAMING ==========
async def stream_audio(controller):
    import websockets
    import json

    audio  = pyaudio.PyAudio()
    stream = None
    try:
        mic_info = audio.get_device_info_by_index(MIC_INDEX)
        logger.info(f"Using: [{MIC_INDEX}] {mic_info['name']}")
        stream = audio.open(
            format=pyaudio.paInt16, channels=1, rate=RATE,
            input=True, input_device_index=MIC_INDEX, frames_per_buffer=CHUNK
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
            logger.info(f"🎤 {DEEPGRAM_LANGUAGE.upper()} | {DEEPGRAM_MODEL.upper()}")
            logger.info("✅ Connected to Deepgram WebSocket")
            logger.info("Press Stop to end\n")

            async def send_audio():
                try:
                    while not _stop_event.is_set():
                        data = await loop.run_in_executor(None, read_audio)
                        await ws.send(data)
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.error(f"Send error: {e}")

            async def recv_transcripts():
                partial_context = ""
                try:
                    async for msg in ws:
                        try:
                            data = json.loads(msg)

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
                                logger.info(f"📝 TRANSCRIPT: {sentence}")

                                partial_context = (partial_context + " " + sentence).strip()
                                found = detect_verse_hybrid(partial_context, controller)

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

            await _stop_event.wait()
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

# ========== SARVAM STREAMING ==========
async def stream_audio_sarvam(controller):
    import base64
    import wave
    import io
    from sarvamai import AsyncSarvamAI

    audio  = pyaudio.PyAudio()
    stream = None
    try:
        mic_info = audio.get_device_info_by_index(MIC_INDEX)
        logger.info(f"Using: [{MIC_INDEX}] {mic_info['name']}")
        stream = audio.open(
            format=pyaudio.paInt16, channels=1, rate=RATE,
            input=True, input_device_index=MIC_INDEX, frames_per_buffer=CHUNK
        )
        logger.info("Microphone opened")
    except Exception as e:
        logger.error(f"Microphone error: {e}")
        return

    def make_wav(pcm_data: bytes) -> str:
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(RATE)
            wf.writeframes(pcm_data)
        return base64.b64encode(buf.getvalue()).decode("utf-8")

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
            high_vad_sensitivity=True,
            vad_signals=True,
        ) as ws:
            logger.info("✅ Sarvam AI connected")
            logger.info(f"🎤 {SARVAM_LANGUAGE} | saaras:v3")

            async def send_audio():
                try:
                    while not _stop_event.is_set():
                        pcm_data = await loop.run_in_executor(None, read_chunk_blocking)
                        wav_b64  = make_wav(pcm_data)
                        await ws.transcribe(audio=wav_b64, encoding="audio/wav", sample_rate=RATE)
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.error(f"Sarvam send error: {e}")

            async def recv_transcripts():
                try:
                    async for message in ws:
                        try:
                            sentence = (
                                getattr(message, "transcript", None)
                                or getattr(message, "text", None)
                                or ""
                            ).strip()
                            if sentence:
                                logger.info(f"📝 TRANSCRIPT: {sentence}")
                                check_verse_queue(sentence, controller)
                                detect_verse_hybrid(sentence, controller)
                        except Exception as e:
                            logger.error(f"Sarvam recv error: {e}")
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.warning(f"Sarvam closed: {e}")

            sender   = asyncio.create_task(send_audio())
            receiver = asyncio.create_task(recv_transcripts())
            await _stop_event.wait()
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

# ========== MAIN ==========
async def main():
    global _stop_event, _engine_loop
    _stop_event  = asyncio.Event()
    _engine_loop = asyncio.get_event_loop()

    controller = VerseController()
    connected  = False

    for attempt in range(1, 6):
        logger.info(f"Connection attempt {attempt}/5...")
        if controller.connect():
            connected = True
            break
        if _stop_event.is_set():
            return
        if attempt < 5:
            logger.warning("⚠️ Retrying in 5s...")
            await asyncio.sleep(5)

    if not connected:
        logger.error("❌ Could not connect to VerseView after 5 attempts.")
        return

    logger.info("=" * 60)
    logger.info("🚀 VerseView Live Started")
    logger.info(f"🎤 Engine: {'Sarvam AI (Malayalam)' if USE_SARVAM else 'Deepgram'}")
    logger.info("=" * 60)

    try:
        if USE_SARVAM:
            await stream_audio_sarvam(controller)
        else:
            await stream_audio(controller)
    finally:
        controller.cleanup()
        logger.info(f"📊 LLM calls: {LLM_CALL_COUNT}")
        logger.info("👋 Shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
