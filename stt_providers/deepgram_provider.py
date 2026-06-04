import asyncio
import json
import logging

from .base import STTProvider
from .utils import open_microphone, teardown_microphone

logger = logging.getLogger("VerseViewSTT")

# Bible book names boosted as keywords when Deepgram is running Hindi (nova-3).
# Helps the model recognise accented English book names (e.g. "Corintens" → "Corinthians").
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


class DeepgramProvider(STTProvider):
    """Real-time Deepgram streaming provider.

    Connects to the Deepgram Nova-3 WebSocket API, streams PCM audio from the
    microphone, and fires on_transcript(...) for every transcript event.

    Partials (is_final=False) are fired so the downstream handler can update
    verse-queue hints in real time.  Finals (is_final=True) carry the full
    sentence for the verse-detection pipeline.
    """

    async def stream_audio(
        self,
        mic_index: int,
        stop_event: asyncio.Event,
        on_transcript,
    ) -> None:
        import websockets  # lazy — not available in every build target

        api_key  = (self.config.get("api_key") or "").strip()
        language = (self.config.get("language") or "en").strip()
        model    = (self.config.get("model") or "nova-3").strip()
        rate     = int(self.config.get("rate") or 16000)
        chunk    = int(self.config.get("chunk") or 4096)
        tag      = (self.config.get("tag") or "[PRI-DG]")

        if not api_key:
            logger.error("❌ Deepgram API key missing — cannot start stream.")
            return

        # Open microphone — bail early if the device is unavailable.
        try:
            audio, stream = open_microphone(mic_index, rate, chunk)
        except RuntimeError as exc:
            logger.error(str(exc))
            return

        # Hindi keyword boosting — improves book-name recognition for Nova-3 Hindi.
        _kw_params = (
            "".join(f"&keyterm={kw}" for kw in _BIBLE_KEYWORDS)
            if language == "hi"
            else ""
        )

        url = (
            f"wss://api.deepgram.com/v1/listen"
            f"?language={language}"
            f"&model={model}"
            f"&punctuate=true"
            f"&smart_format=false"
            f"&interim_results=true"
            f"&utterance_end_ms=1000"
            f"&endpointing=300"
            f"&encoding=linear16"
            f"&sample_rate={rate}"
            f"{_kw_params}"
        )
        headers = {"Authorization": f"Token {api_key}"}
        loop    = asyncio.get_event_loop()

        def _read_audio():
            return stream.read(chunk, exception_on_overflow=False)

        try:
            async with websockets.connect(url, additional_headers=headers) as ws:
                logger.info(f"🎤 {tag} Language: {language.upper()} | Model: {model.upper()}")
                logger.info(f"Connected to Deepgram WebSocket {tag}")
                logger.info("Press Stop to end")

                async def recv_transcripts():
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

                                is_final = bool(data.get("is_final"))

                                if is_final:
                                    # Collapse repeated phrase loops (Deepgram noise artifact).
                                    # When Nova-3 enters a loop it repeats the same 3-token phrase
                                    # many times in a single final result; collapse it so the
                                    # downstream degenerate-chunk guard and transcript buffer
                                    # receive a clean signal rather than a runaway string.
                                    words = sentence.strip().split()
                                    for i in range(len(words) - 6):
                                        phrase = " ".join(words[i : i + 3])
                                        repeat_count = 1
                                        j = i + 3
                                        while j <= len(words) - 3:
                                            if " ".join(words[j : j + 3]) == phrase:
                                                repeat_count += 1
                                                j += 3
                                            else:
                                                break
                                        if repeat_count > 3:
                                            logger.warning(
                                                f"⚠️ {tag} Transcript repetition detected and collapsed"
                                            )
                                            sentence = phrase + "..."
                                            break

                                metadata = {
                                    "tag":        tag,
                                    "confidence": alts[0].get("confidence"),
                                    "raw_type":   msg_type,
                                }
                                on_transcript(sentence, is_final, metadata)

                            except Exception as exc:
                                logger.error(f"Recv error {tag}: {exc}")
                    except asyncio.CancelledError:
                        pass
                    except Exception as exc:
                        logger.warning(f"WebSocket closed {tag}: {exc}")

                async def send_audio():
                    try:
                        while not stop_event.is_set():
                            data = await loop.run_in_executor(None, _read_audio)
                            try:
                                await ws.send(data)
                            except Exception as _send_exc:
                                logger.warning(
                                    f"⚠️ {tag} websocket send error "
                                    f"({type(_send_exc).__name__}) — stopping sender"
                                )
                                break
                    except asyncio.CancelledError:
                        pass
                    except Exception as exc:
                        logger.error(f"Send error {tag}: {exc}")

                sender   = asyncio.create_task(send_audio())
                receiver = asyncio.create_task(recv_transcripts())

                await stop_event.wait()

                sender.cancel()
                receiver.cancel()
                await asyncio.gather(sender, receiver, return_exceptions=True)

                try:
                    await ws.send(json.dumps({"type": "CloseStream"}))
                except Exception:
                    pass

        except asyncio.CancelledError:
            pass
        except Exception as exc:
            err = str(exc)
            if "401" in err:
                logger.error(
                    "❌ Deepgram API key rejected (HTTP 401). "
                    "Check your key in Advanced Settings."
                )
            else:
                logger.error(f"Deepgram WebSocket error {tag}: {exc}")
        finally:
            teardown_microphone(audio, stream, chunk, rate)
