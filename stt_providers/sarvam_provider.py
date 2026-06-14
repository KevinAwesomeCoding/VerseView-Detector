import asyncio
import base64
import logging
import time

from .base import STTProvider
from .utils import open_microphone, teardown_microphone

logger = logging.getLogger("VerseViewSTT")


# Substrings that signal Sarvam credit/quota exhaustion (case-insensitive).
_QUOTA_SIGNALS = ("quota", "credit", "limit exceeded", "insufficient", "balance")


def _is_quota_error(exc) -> bool:
    """True when an exception looks like a Sarvam credit/quota exhaustion signal.

    Detects, case-insensitively:
      • HTTP 402 (Payment Required) / 429 (Too Many Requests) — by status_code
        attribute or as a substring of the error text (the failed websocket
        handshake usually embeds the status / body in the exception message)
      • any of the quota/credit keywords in the exception message
    """
    msg = str(exc).lower()
    if any(sig in msg for sig in _QUOTA_SIGNALS):
        return True
    if "402" in msg or "429" in msg:
        return True
    status = getattr(exc, "status_code", None)
    if status is None:
        status = getattr(exc, "status", None)
    if status in (402, 429):
        return True
    return False


class SarvamProvider(STTProvider):
    """Sarvam AI (saaras:v3) real-time streaming provider for Malayalam.

    Handles WebSocket connect/reconnect, PCM audio delivery, keepalive,
    post-reconnect cooldown, degenerate-chunk filtering, and primary→backup
    API-key fallback on credit/quota exhaustion.

    Malayalam-specific pipeline steps (translation, logging, verse detection)
    are intentionally left to the transcript handler in the main file so that
    verse-detection logic stays co-located with all other engine handlers.

    Config keys:
        api_key           – primary Sarvam API subscription key
        api_key_backup    – backup/personal key used for the rest of the session
                             once the primary key hits a credit/quota error
        on_key_switch     – optional callable() invoked once when the provider
                             switches from the primary key to the backup key
                             (lets the main module flag which key is active)
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

    Fallback behaviour:
        The primary key is used first. On the first credit/quota error it swaps
        to the backup key and reconnects immediately, logging a warning. It never
        switches back during the same session. If the backup key also hits a
        quota error (or no backup key is configured), it logs an error and stops
        the stream gracefully without crashing. No other engine is affected.
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

        api_key_primary = (self.config.get("api_key") or "").strip()
        api_key_backup  = (self.config.get("api_key_backup") or "").strip()
        on_key_switch   = self.config.get("on_key_switch")  # optional callable()
        language_code   = (self.config.get("language_code") or "ml-IN").strip()
        transliteration = bool(self.config.get("transliteration"))
        rate            = int(self.config.get("rate") or 16000)
        chunk           = int(self.config.get("chunk") or 4096)
        tag             = (self.config.get("tag") or "[PRI-ML]")
        drop_fn         = self.config.get("drop_fn")    # optional callable(text, tag) -> bool

        if not api_key_primary:
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

        loop = asyncio.get_event_loop()

        # ── Active-key state ───────────────────────────────────────────────────
        # Starts on the primary key. Switches to backup exactly once, on the first
        # credit/quota error, and never switches back for the rest of the session.
        using_backup = False
        active_key   = api_key_primary
        client       = AsyncSarvamAI(api_subscription_key=active_key)

        # Per-session reconnect cooldown — stored as a one-element list so inner
        # coroutine closures can mutate it without a global declaration.
        _ignore_until = [0.0]

        mode_label = "translit/Manglish" if transliteration else "transcribe/Malayalam"
        mode_param = "translit" if transliteration else "transcribe"

        try:
            while not stop_event.is_set():
                # Holder for a quota error flagged by a child task this iteration.
                _quota_err = [None]

                logger.info(
                    f"Connecting to Sarvam AI "
                    f"({'backup' if using_backup else 'primary'} key)..."
                )
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
                            f"({mode_label}, {'backup' if using_backup else 'primary'} key)"
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
                                        if _is_quota_error(_send_exc):
                                            _quota_err[0] = _send_exc
                                            logger.warning(
                                                f"⚠️ {tag} Sarvam quota error on send "
                                                f"— flagging key fallback"
                                            )
                                            break
                                        logger.warning(
                                            f"⚠️ {tag} send error "
                                            f"({type(_send_exc).__name__}) — "
                                            f"stopping sender; outer loop reconnects"
                                        )
                                        break
                            except asyncio.CancelledError:
                                pass
                            except Exception as exc:
                                if _is_quota_error(exc):
                                    _quota_err[0] = exc
                                else:
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
                                if _is_quota_error(exc):
                                    _quota_err[0] = exc
                                elif not stop_event.is_set():
                                    logger.warning(
                                        f"Sarvam session ended {tag}, "
                                        f"reconnecting: {exc}"
                                    )

                        # ── run until stop, session drop, or quota error ───────
                        sender   = asyncio.create_task(send_audio())
                        pinger   = asyncio.create_task(keepalive())
                        receiver = asyncio.create_task(recv_transcripts())

                        # Wake on stop, on the receiver ending, OR on the sender
                        # ending (a send-side quota error must reconnect/fall back
                        # promptly even while the receiver is still idle-waiting).
                        await asyncio.wait(
                            [
                                asyncio.ensure_future(stop_event.wait()),
                                receiver,
                                sender,
                            ],
                            return_when=asyncio.FIRST_COMPLETED,
                        )

                        sender.cancel()
                        pinger.cancel()
                        receiver.cancel()
                        await asyncio.gather(sender, pinger, receiver, return_exceptions=True)

                        if stop_event.is_set():
                            break

                        # A child task flagged credit/quota exhaustion — route it
                        # through the unified handler below to swap keys or stop.
                        if _quota_err[0] is not None:
                            raise _quota_err[0]

                        logger.info("🔄 Sarvam session ended. Reconnecting in 2s...")
                        await asyncio.sleep(2)

                except asyncio.CancelledError:
                    break
                except Exception as exc:
                    if stop_event.is_set():
                        break

                    # ── Credit / quota exhaustion → key fallback ───────────────
                    if _is_quota_error(exc):
                        if not using_backup:
                            if not api_key_backup:
                                logger.error(
                                    "❌ Sarvam primary key exhausted and no backup "
                                    "key configured — stopping Sarvam stream."
                                )
                                break
                            logger.warning(
                                "⚠️ Sarvam primary key exhausted — switching to backup key"
                            )
                            using_backup = True
                            active_key   = api_key_backup
                            client       = AsyncSarvamAI(api_subscription_key=active_key)
                            if callable(on_key_switch):
                                try:
                                    on_key_switch()
                                except Exception:
                                    pass
                            # Reconnect immediately with the backup key (no retry wait).
                            continue
                        else:
                            logger.error(
                                "❌ Sarvam backup key also failed — stopping Sarvam stream"
                            )
                            break

                    # ── Non-quota error — generic transient retry ──────────────
                    logger.error(f"Sarvam error: {exc} — retrying in 5s...")
                    await asyncio.sleep(5)

        finally:
            teardown_microphone(audio, stream, chunk, rate)
