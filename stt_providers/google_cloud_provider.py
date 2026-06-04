import asyncio
import logging
import os

from .base import STTProvider
from .utils import open_microphone, teardown_microphone

logger = logging.getLogger("VerseViewSTT")

# Reconnect before GCP's hard 305-second (5 min 5 sec) per-session limit.
# 4 min 45 sec gives a 20-second safety margin.
_SESSION_LIMIT_SECS = 285


class GoogleCloudProvider(STTProvider):
    """Real-time Google Cloud Speech-to-Text streaming provider.

    Uses SpeechAsyncClient with bidirectional streaming recognize.  Reconnects
    every _SESSION_LIMIT_SECS (4 min 45 sec) to stay inside GCP's hard 5-minute
    per-session ceiling.

    Connection lifecycle
    --------------------
    1.  Load service account credentials from credentials_path.
    2.  Open the microphone via PyAudio.
    3.  Create a single SpeechAsyncClient (gRPC channel reused across sessions).
    4.  Reconnect loop — per session:
          a.  New stop_session asyncio.Event + per-session error_box.
          b.  Timer task fires stop_session at _SESSION_LIMIT_SECS.
          c.  _audio_gen() yields StreamingRecognizeRequest messages:
                first  → StreamingRecognitionConfig
                rest   → raw PCM audio, one per mic chunk
          d.  _recv() task awaits streaming_recognize(requests=_audio_gen())
              and fires on_transcript for every interim and final result.
          e.  asyncio.wait races stop_event, stop_session, and _recv.
          f.  Teardown: cancel timer + recv, set stop_session to unblock generator.
          g.  Auth errors → break (fatal); quota errors → 30 s back-off; others → reconnect.
    5.  Close gRPC transport.
    6.  teardown_microphone.

    Audio wire format (per StreamingRecognizeRequest after the first)
    -----------------------------------------------------------------
    raw PCM16LE bytes — no base64, no framing.  gRPC handles framing.

    Config keys
    -----------
    credentials_path  – path to a GCP service account JSON key file (required)
    language_code     – BCP-47 language code, e.g. "en-US" (default)
    language          – alias for language_code if language_code is absent
    rate              – PCM sample rate (default 16000)
    chunk             – PyAudio frames_per_buffer (default 4096)
    tag               – log-prefix string (default "[PRI-GCP]")
    model             – GCP recognition model (default "latest_long")
    """

    async def stream_audio(
        self,
        mic_index: int,
        stop_event: asyncio.Event,
        on_transcript,
    ) -> None:
        # ── Lazy imports — not installed in every deployment ────────────────────
        try:
            from google.cloud import speech
            from google.oauth2 import service_account
        except ImportError as _err:
            logger.error(
                f"❌ google-cloud-speech or google-auth not installed. "
                f"Run: pip install google-cloud-speech  (detail: {_err})"
            )
            return

        # ── Config ──────────────────────────────────────────────────────────────
        credentials_path = (self.config.get("credentials_path") or "").strip()
        language_code    = (
            self.config.get("language_code")
            or self.config.get("language")
            or "en-US"
        ).strip()
        rate  = int(self.config.get("rate") or 16000)
        chunk = int(self.config.get("chunk") or 4096)
        tag   = (self.config.get("tag") or "[PRI-GCP]")
        model = (self.config.get("model") or "latest_long").strip()

        # ── Credentials ─────────────────────────────────────────────────────────
        if not credentials_path:
            logger.error(
                "❌ Google Cloud credentials path missing — cannot start stream. "
                "Set gcp_credentials_path in Advanced Settings."
            )
            return

        if not os.path.isfile(credentials_path):
            logger.error(
                f"❌ GCP credentials file not found: {credentials_path}"
            )
            return

        try:
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
        except Exception as exc:
            logger.error(f"❌ Failed to load GCP credentials: {exc}")
            return

        # ── Microphone — bail early so teardown never runs with None handles ────
        try:
            audio, stream = open_microphone(mic_index, rate, chunk)
        except RuntimeError as exc:
            logger.error(str(exc))
            return

        # ── GCP client — created once; channel is reused across sessions ────────
        loop   = asyncio.get_event_loop()
        client = speech.SpeechAsyncClient(credentials=credentials)

        # Recognition config is identical for every session in this run.
        recognition_config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=rate,
            language_code=language_code,
            enable_automatic_punctuation=True,
            model=model,
        )
        streaming_config = speech.StreamingRecognitionConfig(
            config=recognition_config,
            interim_results=True,
        )

        def _read_audio():
            return stream.read(chunk, exception_on_overflow=False)

        logger.info(
            f"🎤 {tag} Google Cloud STT initialised — "
            f"language: {language_code} | model: {model}"
        )

        try:
            # ── Reconnect loop ──────────────────────────────────────────────────
            while not stop_event.is_set():
                # Per-session state — each iteration gets its own Event and error box
                # so closures from previous iterations cannot interfere.
                stop_session = asyncio.Event()
                error_box: list = []

                # ── Session timer ───────────────────────────────────────────────
                # GCP closes the stream at 305 s.  Set stop_session at 285 s so the
                # audio generator drains cleanly before the server terminates.
                async def _session_timer():
                    try:
                        await asyncio.sleep(_SESSION_LIMIT_SECS)
                        if not stop_event.is_set():
                            logger.info(
                                f"⏱️ {tag} GCP session limit ({_SESSION_LIMIT_SECS}s) — "
                                f"reconnecting..."
                            )
                            stop_session.set()
                    except asyncio.CancelledError:
                        pass

                timer_task = asyncio.create_task(_session_timer())

                # ── Audio generator ─────────────────────────────────────────────
                async def _audio_gen():
                    # The first request must carry StreamingRecognitionConfig.
                    yield speech.StreamingRecognizeRequest(
                        streaming_config=streaming_config
                    )
                    # All subsequent requests carry raw PCM16LE audio content.
                    while not stop_event.is_set() and not stop_session.is_set():
                        pcm = await loop.run_in_executor(None, _read_audio)
                        yield speech.StreamingRecognizeRequest(audio_content=pcm)

                # ── Response task ───────────────────────────────────────────────
                async def _recv():
                    try:
                        # streaming_recognize is async def — await it to obtain the
                        # async response iterator, then iterate over results normally.
                        responses = await client.streaming_recognize(
                            requests=_audio_gen()
                        )
                        async for response in responses:
                            if stop_event.is_set() or stop_session.is_set():
                                break
                            for result in response.results:
                                if not result.alternatives:
                                    continue
                                sentence = result.alternatives[0].transcript.strip()
                                if not sentence:
                                    continue
                                is_final   = result.is_final
                                confidence = (
                                    result.alternatives[0].confidence
                                    if is_final
                                    else None
                                )
                                metadata = {
                                    "engine":        "gcp",
                                    "tag":           tag,
                                    "confidence":    confidence,
                                    "language_code": language_code,
                                    "raw":           str(result),
                                }
                                if is_final:
                                    logger.info(f"📝 {tag} {sentence}")
                                on_transcript(sentence, is_final, metadata)
                    except asyncio.CancelledError:
                        pass
                    except Exception as exc:
                        # Only surface errors that aren't caused by our own shutdown.
                        if not stop_event.is_set() and not stop_session.is_set():
                            error_box.append(exc)

                recv_task = asyncio.create_task(_recv())
                logger.info(f"Connecting to Google Cloud STT {tag}...")

                # ── Race stop_event, session limit, or unexpected recv exit ──────
                # Using ensure_future wraps coroutines as Tasks so asyncio.wait
                # can race them against the already-created recv_task.
                stop_future    = asyncio.ensure_future(stop_event.wait())
                session_future = asyncio.ensure_future(stop_session.wait())
                try:
                    await asyncio.wait(
                        {stop_future, session_future, recv_task},
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                finally:
                    # Always cancel the stop/session futures to prevent task leaks.
                    stop_future.cancel()
                    session_future.cancel()

                # ── Ordered teardown ────────────────────────────────────────────
                # Set stop_session first so the audio generator exits its while-loop
                # on its next iteration, avoiding a blocked run_in_executor hang.
                stop_session.set()
                timer_task.cancel()
                recv_task.cancel()
                await asyncio.gather(timer_task, recv_task, return_exceptions=True)

                # ── Error routing ────────────────────────────────────────────────
                if error_box and not stop_event.is_set():
                    exc     = error_box[0]
                    err_str = str(exc)
                    if any(
                        code in err_str
                        for code in ("UNAUTHENTICATED", "PERMISSION_DENIED")
                    ):
                        logger.error(
                            f"❌ GCP credentials rejected. "
                            f"Check your service account key.  Detail: {exc}"
                        )
                        break   # auth failure — reconnecting will not help
                    if "RESOURCE_EXHAUSTED" in err_str:
                        logger.warning(
                            f"⚠️ {tag} GCP quota exhausted — retrying in 30s..."
                        )
                        await asyncio.sleep(30)
                        continue
                    logger.error(f"GCP session error {tag}: {exc}")

                if stop_event.is_set():
                    break

                logger.info(f"🔄 {tag} Reconnecting to Google Cloud STT in 1s...")
                await asyncio.sleep(1)

        except asyncio.CancelledError:
            pass

        finally:
            logger.info(f"🛑 {tag} Google Cloud STT provider stopped.")
            try:
                # Close the underlying gRPC channel.  The transport's close() is a
                # coroutine on grpc.aio transports; handle both sync and async forms.
                result = client.transport.close()
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                pass
            teardown_microphone(audio, stream, chunk, rate)
