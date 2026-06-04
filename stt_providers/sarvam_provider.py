import asyncio
import base64
import logging
import time

from .base import STTProvider
from .utils import open_microphone, teardown_microphone

logger = logging.getLogger("VerseViewSTT")


class SarvamProvider(STTProvider):
    """Sarvam AI (saaras:v3) real-time streaming provider for Malayalam.

    Handles WebSocket connect/reconnect, PCM audio delivery, keepalive,
    post-reconnect cooldown, and degenerate-chunk filtering.

    Malayalam-specific pipeline steps (translation, logging, verse detection)
    are intentionally left to the transcript handler in the main file so that
    verse-detection logic stays co-located with all other engine handlers.

    Config keys:
        api_key           – Sarvam API subscription key
        language_code     – BCP-47 code, e.g. "ml-IN" (default)
        transliteration   – bool; True → "translit" mode (Manglish output),
                             False → "transcribe" mode (native Malayalam)
        rate              – PCM sample rate (e.g. 16000)
        chunk             – PyAudio frames_per_buffer
        tag               – log-prefix string, e.g. "[PRI-ML]"
        drop_fn           – optional callable(text, tag) → bool;
                             if it returns True the raw sentence is discarded
                             before the handler is invoked (avoids a translation
                             API call on degenerate/repetition garbage)
    """

    async def stream_audio(
        self,
        mic_index: int,
        stop_event: asyncio.Event,
        on_transcript,
    ) -> None:
        import base64  # noqa: F811 (already at module level, re-import is harmless)
        try:
            from sarvamai import AsyncSarvamAI
        except ImportError as _err:
            logger.error(
                f"❌ sarvamai SDK not installed. "
                f"Run: pip install sarvamai  (detail: {_err})"
            )
            return

        api_key        = (self.config.get("api_key") or "").strip()
        language_code  = (self.config.get("language_code") or "ml-IN").strip()
        transliteration = bool(self.config.get("transliteration"))
        rate           = int(self.config.get("rate") or 16000)
        chunk          = int(self.config.get("chunk") or 4096)
        tag            = (self.config.get("tag") or "[PRI-ML]")
        drop_fn        = self.config.get("drop_fn")    # optional callable(text, tag) -> bool

        if not api_key:
            logger.error("❌ Sarvam API key missing — cannot start stream.")
            return

        # Open microphone — bail early if the device is unavailable.
        try:
            audio, stream = open_microphone(mic_index, rate, chunk)
        except RuntimeError as exc:
            logger.error(str(exc))
            return

        # Sarvam expects half-second PCM bursts; we batch CHUNK-sized reads.
        _chunks_per_burst = max(1, int(rate * 0.5 / chunk))

        def _read_burst_blocking():
            frames = []
            for _ in range(_chunks_per_burst):
                frames.append(stream.read(chunk, exception_on_overflow=False))
            return b"".join(frames)

        client = AsyncSarvamAI(api_subscription_key=api_key)
        loop   = asyncio.get_event_loop()

        # Per-session reconnect cooldown — stored as a one-element list so inner
        # coroutine closures can mutate it without a global declaration.
        _ignore_until = [0.0]

        mode_label = "translit/Manglish" if transliteration else "transcribe/Malayalam"
        mode_param = "translit" if transliteration else "transcribe"

        try:
            while not stop_event.is_set():
                logger.info("Connecting to Sarvam AI...")
                try:
                    async with client.speech_to_text_streaming.connect(
                        model="saaras:v3",
                        # mode controls output format:
                        #   "transcribe" → native Malayalam text (default for sermons)
                        #   "translit"   → Roman/Manglish script
                        mode=mode_param,
                        language_code=language_code,
                        sample_rate=rate,
                        # high_vad_sensitivity=True: ~0.5s silence commits a segment;
                        # appropriate for sermon pacing (natural breath pause > 0.5s).
                        high_vad_sensitivity=True,
                        vad_signals=False,
                        input_audio_codec="pcm_s16le",
                    ) as ws:
                        logger.info(
                            f"Sarvam AI connected — {language_code} saaras:v3 "
                            f"({mode_label})"
                        )
                        # Discard 3 s of audio after every (re)connect to avoid
                        # the model transcribing mid-sentence noise at the boundary.
                        _ignore_until[0] = time.time() + 3.0
                        logger.info("⏳ Ignoring post-reconnect audio (3s cooldown)")

                        # ── send_audio ─────────────────────────────────────────
                        async def send_audio():
                            try:
                                while not stop_event.is_set():
                                    burst = await loop.run_in_executor(
                                        None, _read_burst_blocking
                                    )
                                    try:
                                        await ws.transcribe(
                                            audio=base64.b64encode(burst).decode("utf-8")
                                        )
                                    except Exception as _send_exc:
                                        logger.warning(
                                            f"⚠️ {tag} send error "
                                            f"({type(_send_exc).__name__}) — "
                                            f"stopping sender; outer loop reconnects"
                                        )
                                        break
                            except asyncio.CancelledError:
                                pass
                            except Exception as exc:
                                logger.error(f"Sarvam send error {tag}: {exc}")

                        # ── keepalive ──────────────────────────────────────────
                        # Sarvam's WebSocket drops idle connections after ~30 s.
                        # Sending a silent burst every 25 s keeps the session alive
                        # without producing false transcript events.
                        async def keepalive():
                            _silence = b"\x00" * chunk * 2
                            try:
                                while not stop_event.is_set():
                                    try:
                                        await asyncio.wait_for(
                                            stop_event.wait(), timeout=25
                                        )
                                        break  # stop_event fired
                                    except asyncio.TimeoutError:
                                        pass
                                    if stop_event.is_set():
                                        break
                                    try:
                                        await ws.transcribe(
                                            audio=base64.b64encode(_silence).decode("utf-8")
                                        )
                                    except Exception:
                                        pass
                            except asyncio.CancelledError:
                                pass
                            except Exception:
                                pass

                        # ── recv_transcripts ───────────────────────────────────
                        async def recv_transcripts():
                            try:
                                async for message in ws:
                                    try:
                                        # Bug 7: SDK returns SpeechToTextStreamingResponse
                                        # objects, not plain dicts.
                                        if isinstance(message, dict):
                                            raw = message.get(
                                                "transcript", message.get("text", "")
                                            )
                                        else:
                                            raw = (
                                                getattr(message.data, "transcript", "")
                                                if hasattr(message, "data")
                                                else getattr(
                                                    message,
                                                    "transcript",
                                                    getattr(message, "text", ""),
                                                )
                                            )

                                        raw = str(raw).strip()
                                        if not raw or raw == "None":
                                            continue

                                        # Post-reconnect cooldown: discard boundary noise.
                                        if time.time() < _ignore_until[0]:
                                            continue

                                        # Degenerate-chunk guard — applied before calling
                                        # the handler so a translation API call is not
                                        # wasted on hallucination garbage.
                                        if drop_fn and drop_fn(raw, tag):
                                            continue

                                        on_transcript(
                                            raw,
                                            True,   # Sarvam fires per utterance — always final
                                            {
                                                "mode":        mode_param,
                                                "language":    language_code,
                                                "tag":         tag,
                                            },
                                        )

                                    except Exception as exc:
                                        logger.error(
                                            f"Sarvam message error {tag}: {exc}"
                                        )

                            except asyncio.CancelledError:
                                pass
                            except Exception as exc:
                                if not stop_event.is_set():
                                    logger.warning(
                                        f"Sarvam session ended {tag}, "
                                        f"reconnecting: {exc}"
                                    )

                        # ── run until stop or session drop ─────────────────────
                        sender   = asyncio.create_task(send_audio())
                        pinger   = asyncio.create_task(keepalive())
                        receiver = asyncio.create_task(recv_transcripts())

                        await asyncio.wait(
                            [asyncio.ensure_future(stop_event.wait()), receiver],
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

                except asyncio.CancelledError:
                    break
                except Exception as exc:
                    if stop_event.is_set():
                        break
                    logger.error(f"Sarvam error: {exc} — retrying in 5s...")
                    await asyncio.sleep(5)

        finally:
            teardown_microphone(audio, stream, chunk, rate)
