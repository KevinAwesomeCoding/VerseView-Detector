import asyncio
import io
import logging
import wave

from .base import STTProvider
from .utils import open_microphone, teardown_microphone

logger = logging.getLogger("VerseViewSTT")

# Each audio segment posted to the Whisper endpoint is this many seconds long.
# 4 s gives Whisper enough phonetic context without excessive latency.
_SEGMENT_SECS = 4


def _build_wav_bytes(pcm_frames: bytes, rate: int, channels: int = 1) -> bytes:
    """Wrap raw PCM16LE bytes in a minimal WAV container.

    Returns the WAV as an in-memory bytes object suitable for multipart upload.
    """
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)          # 16-bit = 2 bytes per sample
        wf.setframerate(rate)
        wf.writeframes(pcm_frames)
    return buf.getvalue()


class LocalWhisperProvider(STTProvider):
    """Local Whisper STT provider — chunked audio buffer + HTTP POST.

    Buffers mic audio into fixed _SEGMENT_SECS-second WAV blobs and POSTs each
    one to a locally hosted Whisper endpoint (e.g. faster-whisper-server,
    whisper.cpp server, or any OpenAI-compatible /audio/transcriptions endpoint).

    All results are emitted as is_final=True because each POST covers a
    completed, non-overlapping audio segment.

    Buffer strategy
    ---------------
    For each segment:
      1.  Accumulate frames_per_segment = rate * _SEGMENT_SECS raw PCM reads.
      2.  Each read is `chunk` frames via run_in_executor so the event loop
          stays unblocked.
      3.  stop_event is checked between every read and between every segment.
      4.  When stop_event fires mid-segment, the partial buffer is discarded
          (a partial segment is too short for reliable Whisper transcription).
      5.  On POST failure the segment is logged and skipped — no crash, no retry.

    Endpoint contract
    -----------------
    POST {endpoint}          if the configured URL already ends with a path
    POST {endpoint}/transcribe  as a fallback if no path is present

    Request:  multipart/form-data with field "file" = WAV bytes (filename audio.wav)
    Response: JSON with at least a "text" field, e.g.:
                {"text": "John chapter three verse sixteen"}
              Also accepts OpenAI-compatible {"choices": [{"text": "..."}]} shape.

    Config keys
    -----------
    endpoint  – base URL of the local Whisper server (required)
    rate      – PCM sample rate (default 16000)
    chunk     – PyAudio frames_per_buffer (default 4096)
    tag       – log-prefix string (default "[PRI-WH]")
    language  – language hint passed to the endpoint if supported (default "en")
    """

    async def stream_audio(
        self,
        mic_index: int,
        stop_event: asyncio.Event,
        on_transcript,
    ) -> None:
        # ── Lazy import — aiohttp is not guaranteed in every build target ───────
        try:
            import aiohttp
        except ImportError as _err:
            logger.error(
                f"❌ aiohttp not installed. "
                f"Run: pip install aiohttp  (detail: {_err})"
            )
            return

        # ── Config ──────────────────────────────────────────────────────────────
        endpoint = (self.config.get("endpoint") or "").strip().rstrip("/")
        rate     = int(self.config.get("rate") or 16000)
        chunk    = int(self.config.get("chunk") or 4096)
        tag      = (self.config.get("tag") or "[PRI-WH]")
        language = (self.config.get("language") or "en").strip()

        if not endpoint:
            logger.error(
                "❌ Local Whisper endpoint missing — cannot start stream. "
                "Set local_whisper_endpoint in Advanced Settings."
            )
            return

        # The endpoint is the full POST URL as returned by ensure_whisper_server()
        # e.g. http://127.0.0.1:8000/v1/audio/transcriptions
        post_url = endpoint

        # ── Microphone ──────────────────────────────────────────────────────────
        try:
            audio, stream = open_microphone(mic_index, rate, chunk)
        except RuntimeError as exc:
            logger.error(str(exc))
            return

        loop = asyncio.get_event_loop()

        # Number of PyAudio reads needed to fill one _SEGMENT_SECS window.
        reads_per_segment = max(1, int(rate * _SEGMENT_SECS / chunk))
        actual_segment_secs = (reads_per_segment * chunk) / rate

        def _read_audio():
            return stream.read(chunk, exception_on_overflow=False)

        logger.info(
            f"🎤 {tag} Local Whisper started — endpoint: {post_url} | "
            f"segment: {actual_segment_secs:.1f}s | language: {language}"
        )

        # Single persistent aiohttp session for the duration of the run.
        connector = aiohttp.TCPConnector(limit=2)
        session   = aiohttp.ClientSession(connector=connector)

        try:
            while not stop_event.is_set():
                # ── Accumulate one audio segment ────────────────────────────────
                raw_frames: list[bytes] = []
                segment_complete = True

                for _ in range(reads_per_segment):
                    if stop_event.is_set():
                        segment_complete = False
                        break
                    try:
                        pcm = await loop.run_in_executor(None, _read_audio)
                        raw_frames.append(pcm)
                    except Exception as exc:
                        logger.warning(f"⚠️ {tag} mic read error: {exc}")
                        segment_complete = False
                        break

                if not segment_complete or not raw_frames:
                    break

                # ── Build WAV blob ───────────────────────────────────────────────
                pcm_bytes = b"".join(raw_frames)
                wav_bytes  = _build_wav_bytes(pcm_bytes, rate)

                # ── POST to Whisper endpoint ─────────────────────────────────────
                logger.debug(
                    f"⬆️ {tag} POSTing {len(wav_bytes) // 1024} KB "
                    f"({actual_segment_secs:.1f}s) to {post_url}"
                )

                try:
                    form = aiohttp.FormData()
                    form.add_field(
                        "file",
                        wav_bytes,
                        filename="audio.wav",
                        content_type="audio/wav",
                    )
                    form.add_field("model", "whisper-1")
                    form.add_field("response_format", "json")

                    async with session.post(
                        post_url,
                        data=form,
                        timeout=aiohttp.ClientTimeout(total=30),
                    ) as resp:
                        if resp.status != 200:
                            body = await resp.text()
                            logger.warning(
                                f"⚠️ {tag} Whisper endpoint returned HTTP "
                                f"{resp.status}: {body[:120]}"
                            )
                            continue

                        raw_json = await resp.json(content_type=None)

                except asyncio.CancelledError:
                    break
                except aiohttp.ClientConnectorError as exc:
                    logger.error(
                        f"❌ {tag} Cannot reach Whisper endpoint {post_url}: {exc}. "
                        "Check that your local server is running."
                    )
                    # Brief pause before retrying so we don't flood logs if the
                    # server is starting up.
                    await asyncio.sleep(2)
                    continue
                except Exception as exc:
                    logger.error(f"⚠️ {tag} Whisper POST error: {exc}")
                    continue

                # ── Extract transcript text ──────────────────────────────────────
                # OpenAI-compatible /v1/audio/transcriptions returns {"text": "..."}
                sentence = ""
                if isinstance(raw_json, dict):
                    sentence = raw_json.get("text", "").strip()

                if not sentence:
                    logger.debug(f"… {tag} empty segment (silence or noise)")
                    continue

                metadata = {
                    "engine":            "local_whisper",
                    "tag":               tag,
                    "chunk_duration_sec": actual_segment_secs,
                    "raw":               raw_json,
                }

                logger.info(f"📝 {tag} {sentence}")
                on_transcript(sentence, True, metadata)

        except asyncio.CancelledError:
            pass

        finally:
            logger.info(f"🛑 {tag} Local Whisper provider stopped.")
            try:
                await session.close()
            except Exception:
                pass
            teardown_microphone(audio, stream, chunk, rate)
