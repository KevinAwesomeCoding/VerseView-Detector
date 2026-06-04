import asyncio
import logging
import threading

from .base import STTProvider
from .utils import open_microphone, teardown_microphone

logger = logging.getLogger("VerseViewSTT")


class AssemblyAIProvider(STTProvider):
    """Real-time AssemblyAI Universal-3 streaming provider.

    Uses the AssemblyAI streaming SDK (v3).  Audio is read from a PyAudio mic
    in a blocking thread (via run_in_executor) and bridged to the async consumer
    through an asyncio.Queue.  A threading.Event mirrors stop_event so the
    blocking generator in the executor thread can exit cleanly.

    Includes a reconnect loop (matching Sarvam's pattern) and a periodic
    force_endpoint task so long sentences are committed within turn_cutoff
    seconds even when the speaker pauses less than the model's VAD threshold.
    """

    async def stream_audio(
        self,
        mic_index: int,
        stop_event: asyncio.Event,
        on_transcript,
    ) -> None:
        api_key     = (self.config.get("api_key") or "").strip()
        language    = (self.config.get("language") or "en").strip()
        turn_cutoff = max(3, min(11, int(self.config.get("turn_cutoff") or 5)))
        rate        = int(self.config.get("rate") or 16000)
        chunk       = int(self.config.get("chunk") or 4096)
        tag         = (self.config.get("tag") or "[PRI-AAI]")

        if not api_key:
            logger.error("❌ AssemblyAI API key missing — cannot start stream.")
            return

        # Lazy SDK import — not every build target installs assemblyai.
        try:
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
                f"❌ AssemblyAI SDK not installed or version too old. "
                f"Run: pip install -U assemblyai  (detail: {_aai_err})"
            )
            return

        # Open microphone — bail early if the device is unavailable.
        try:
            audio, stream = open_microphone(mic_index, rate, chunk)
        except RuntimeError as exc:
            logger.error(str(exc))
            return

        # Speech model selection — universal-multilingual handles hi/ml/multi;
        # u3-rt-pro is the English-only Pro model.
        if language in ("hi", "ml", "multi"):
            _aai_model   = "universal-streaming-multilingual"
            _lang_detect = (language == "multi")
        else:
            _aai_model   = "u3-rt-pro"
            _lang_detect = False

        _model_label = {
            "u3-rt-pro":                       "Universal-3 Pro (English)",
            "universal-streaming-multilingual": "Universal-3 Multilingual",
        }.get(_aai_model, _aai_model)

        loop              = asyncio.get_event_loop()
        _stop_mirror      = threading.Event()
        _transcript_queue: asyncio.Queue = asyncio.Queue()

        try:
            # ── Reconnect loop ──────────────────────────────────────────────────
            while not stop_event.is_set():
                _stop_mirror.clear()

                # ── Audio generator (executor thread) ───────────────────────────
                def _audio_generator():
                    """Yield raw PCM chunks until stop is signalled."""
                    while not _stop_mirror.is_set() and not stop_event.is_set():
                        try:
                            yield stream.read(chunk, exception_on_overflow=False)
                        except Exception:
                            break

                # ── SDK event callbacks (called from SDK thread) ─────────────────
                def _on_turn(client: StreamingClient, event: TurnEvent):
                    """Commit the turn only when end_of_turn fires."""
                    if not event.end_of_turn:
                        return
                    sentence = (event.transcript or "").strip()
                    if not sentence:
                        return
                    loop.call_soon_threadsafe(_transcript_queue.put_nowait, sentence)

                def _on_error(client: StreamingClient, error: Exception):
                    logger.error(f"⚠️ {tag} AssemblyAI streaming error: {error}")
                    _stop_mirror.set()   # unblock generator; outer loop reconnects

                def _on_begin(client: StreamingClient, info: BeginEvent):
                    logger.info(f"🎤 {tag} AssemblyAI session: {info.id}")

                # ── SDK client setup ─────────────────────────────────────────────
                params = StreamingParameters(
                    sample_rate=rate,
                    speech_model=_aai_model,
                    format_turns=True,
                    language_detection=_lang_detect or None,
                    min_turn_silence=300,   # 300 ms silence commits the turn
                )
                client_opts = StreamingClientOptions(
                    api_key=api_key,
                    base_url="wss://streaming.assemblyai.com/v3/ws",
                )
                client = StreamingClient(client_opts)
                client.on(StreamingEvents.Turn,  _on_turn)
                client.on(StreamingEvents.Error, _on_error)
                client.on(StreamingEvents.Begin, _on_begin)

                logger.info(f"🎤 {tag} Connecting — {_model_label} / lang={language}...")

                # ── Blocking SDK runner (executor) ───────────────────────────────
                def _run_client():
                    try:
                        client.connect(params)
                        client.stream(_audio_generator())
                    except Exception as exc:
                        if not stop_event.is_set():
                            logger.error(f"{tag} AssemblyAI client error: {exc}")
                    finally:
                        _stop_mirror.set()

                executor_future = loop.run_in_executor(None, _run_client)

                # ── Periodic force_endpoint (prevents stuck long sentences) ─────
                async def _force_endpoint_loop():
                    try:
                        while not stop_event.is_set() and not _stop_mirror.is_set():
                            await asyncio.sleep(turn_cutoff)
                            if stop_event.is_set() or _stop_mirror.is_set():
                                break
                            try:
                                await loop.run_in_executor(None, client.force_endpoint)
                            except Exception:
                                pass
                    except asyncio.CancelledError:
                        pass

                _force_task = asyncio.ensure_future(_force_endpoint_loop())

                # ── Async transcript consumer ────────────────────────────────────
                try:
                    while not stop_event.is_set():
                        try:
                            sentence = await asyncio.wait_for(
                                _transcript_queue.get(), timeout=0.5
                            )
                        except asyncio.TimeoutError:
                            if executor_future.done():
                                break
                            continue

                        if not sentence:
                            continue

                        on_transcript(sentence, True, {"tag": tag})

                finally:
                    # ── Ordered teardown ─────────────────────────────────────────
                    _force_task.cancel()
                    try:
                        await asyncio.wait_for(asyncio.shield(_force_task), timeout=1.0)
                    except Exception:
                        pass

                    _stop_mirror.set()   # unblock audio generator thread

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

                logger.info(f"🔄 {tag} Session ended. Reconnecting in 2s...")
                await asyncio.sleep(2)

        except asyncio.CancelledError:
            pass
        finally:
            teardown_microphone(audio, stream, chunk, rate)
