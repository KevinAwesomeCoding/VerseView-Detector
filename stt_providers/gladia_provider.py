import asyncio
import base64
import json
import logging

from .base import STTProvider
from .utils import open_microphone, teardown_microphone

logger = logging.getLogger("VerseViewSTT")

# Gladia v2 realtime WebSocket endpoint.
_GLADIA_WS_URL = "wss://api.gladia.io/audio/text/audio-transcription"


class GladiaProvider(STTProvider):
    """Real-time Gladia v2 streaming provider.

    Streams PCM16 audio to the Gladia WebSocket API and fires
    on_transcript(sentence, is_final, metadata) for every partial and final
    transcript event.

    Connection lifecycle
    --------------------
    1.  Open the microphone via PyAudio.
    2.  Connect to the Gladia WebSocket with the API key in the
        ``x-gladia-key`` header.
    3.  Concurrently run send_audio() and recv_transcripts().
    4.  On stop_event: cancel both tasks, send the Gladia end-of-stream
        signal (``{"frames": ""}``), then close.
    5.  If the session drops before stop_event fires, reconnect automatically
        after a brief pause.
    6.  Auth errors (HTTP 401/403) are treated as fatal — no reconnect.

    Audio wire format (each send)
    -----------------------------
    {
        "frames":      "<base64-encoded PCM16LE>",
        "sample_rate": <int>,
        "bit_depth":   16,
        "channels":    1
    }

    Transcript event wire format (each receive)
    --------------------------------------------
    Gladia v2 emits either a flat object or a nested envelope:

      Flat:    {"transcription": "...", "type": "final"|"partial",
                "confidence": 0.95, "language": "en",
                "time_begin": 1.0, "time_end": 2.0}

      Nested:  {"event": "transcript", "data": { ...same fields... }}

    Both forms are normalised before firing on_transcript.

    Config keys
    -----------
    api_key   – Gladia API key (required)
    language  – BCP-47 language code passed to the API, e.g. "en" (default)
    rate      – PCM sample rate, e.g. 16000 (default)
    chunk     – PyAudio frames_per_buffer, e.g. 4096 (default)
    tag       – log-prefix string, e.g. "[PRI-GL]" (default)
    """

    async def stream_audio(
        self,
        mic_index: int,
        stop_event: asyncio.Event,
        on_transcript,
    ) -> None:
        import websockets  # lazy — not present in every build target

        api_key  = (self.config.get("api_key") or "").strip()
        language = (self.config.get("language") or "en").strip()
        rate     = int(self.config.get("rate") or 16000)
        chunk    = int(self.config.get("chunk") or 4096)
        tag      = (self.config.get("tag") or "[PRI-GL]")

        if not api_key:
            logger.error(
                "❌ Gladia API key missing — cannot start stream. "
                "Set gladia_api_key in Advanced Settings."
            )
            return

        # Open microphone — bail early so teardown never runs with None handles.
        try:
            audio, stream = open_microphone(mic_index, rate, chunk)
        except RuntimeError as exc:
            logger.error(str(exc))
            return

        loop    = asyncio.get_event_loop()
        headers = {"x-gladia-key": api_key}

        def _read_audio():
            return stream.read(chunk, exception_on_overflow=False)

        try:
            # ── Reconnect loop ──────────────────────────────────────────────────
            while not stop_event.is_set():
                logger.info(f"Connecting to Gladia WebSocket {tag}...")

                try:
                    async with websockets.connect(
                        _GLADIA_WS_URL,
                        additional_headers=headers,
                    ) as ws:
                        logger.info(
                            f"🎤 {tag} Gladia connected — language: {language.upper()}"
                        )
                        logger.info("Press Stop to end")

                        # ── send_audio ──────────────────────────────────────────
                        async def send_audio():
                            """Read PCM chunks from the mic and post them to Gladia.

                            Continuous audio flow also serves as the session
                            keepalive — no separate ping is needed.
                            """
                            try:
                                while not stop_event.is_set():
                                    raw = await loop.run_in_executor(None, _read_audio)
                                    payload = json.dumps({
                                        "frames":      base64.b64encode(raw).decode("utf-8"),
                                        "sample_rate": rate,
                                        "bit_depth":   16,
                                        "channels":    1,
                                    })
                                    try:
                                        await ws.send(payload)
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
                                logger.error(f"Gladia send error {tag}: {exc}")

                        # ── recv_transcripts ────────────────────────────────────
                        async def recv_transcripts():
                            """Parse Gladia transcript events and fire on_transcript.

                            Gladia v2 may emit an envelope with an "event" key or a
                            flat object — both are normalised to the same inner dict
                            before field extraction.
                            """
                            try:
                                async for msg in ws:
                                    try:
                                        data = (
                                            json.loads(msg)
                                            if isinstance(msg, str)
                                            else msg
                                        )

                                        # Normalise nested envelope vs flat object.
                                        if "event" in data:
                                            event_name = data.get("event", "")
                                            # Skip non-transcript events such as
                                            # "connected" or "error".
                                            if event_name not in ("transcript", ""):
                                                continue
                                            inner = data.get("data", data)
                                        else:
                                            inner = data

                                        sentence = (
                                            inner.get("transcription") or ""
                                        ).strip()
                                        if not sentence:
                                            continue

                                        event_type = (
                                            inner.get("type") or "final"
                                        ).lower()
                                        is_final   = (event_type == "final")
                                        confidence = inner.get("confidence")

                                        metadata = {
                                            "engine":     "gladia",
                                            "tag":        tag,
                                            "confidence": confidence,
                                            "language":   inner.get("language", language),
                                            "time_begin": inner.get("time_begin"),
                                            "time_end":   inner.get("time_end"),
                                            "raw":        data,
                                        }

                                        logger.debug(
                                            f"{'📝' if is_final else '…'} {tag} "
                                            f"[{'FINAL' if is_final else 'partial'}] "
                                            f"{sentence}"
                                        )
                                        on_transcript(sentence, is_final, metadata)

                                    except Exception as exc:
                                        logger.error(f"Gladia recv error {tag}: {exc}")

                            except asyncio.CancelledError:
                                pass
                            except Exception as exc:
                                if not stop_event.is_set():
                                    logger.warning(
                                        f"Gladia session ended {tag}: {exc}"
                                    )

                        sender   = asyncio.create_task(send_audio())
                        receiver = asyncio.create_task(recv_transcripts())

                        # Wait for stop_event OR for the session to drop.
                        # A stop_future wraps stop_event.wait() so asyncio.wait()
                        # can race it against the receiver task.  Cancel it after
                        # the race to prevent a task leak.
                        stop_future = asyncio.ensure_future(stop_event.wait())
                        try:
                            await asyncio.wait(
                                {stop_future, receiver},
                                return_when=asyncio.FIRST_COMPLETED,
                            )
                        finally:
                            stop_future.cancel()

                        sender.cancel()
                        receiver.cancel()
                        await asyncio.gather(sender, receiver, return_exceptions=True)

                        # Politely signal end-of-stream before the WebSocket
                        # context manager closes the connection.
                        try:
                            await asyncio.wait_for(
                                ws.send(json.dumps({"frames": ""})),
                                timeout=2.0,
                            )
                        except Exception:
                            pass

                        if stop_event.is_set():
                            break

                        # Session dropped unexpectedly — reconnect.
                        logger.info(
                            f"🔄 {tag} Gladia session dropped — reconnecting in 2s..."
                        )
                        await asyncio.sleep(2)

                except asyncio.CancelledError:
                    break

                except Exception as exc:
                    if stop_event.is_set():
                        break
                    err = str(exc)
                    if "401" in err or "403" in err:
                        logger.error(
                            f"❌ Gladia API key rejected ({err[:60]}). "
                            "Check your key in Advanced Settings."
                        )
                        break   # auth failure — reconnecting will not help
                    logger.error(
                        f"Gladia connection error {tag}: {exc} — retrying in 5s..."
                    )
                    await asyncio.sleep(5)

        except asyncio.CancelledError:
            pass

        finally:
            logger.info(f"🛑 {tag} Gladia provider stopped.")
            teardown_microphone(audio, stream, chunk, rate)
