import asyncio
import logging
import os
import time

from .base import STTProvider
from .utils import open_microphone, teardown_microphone

logger = logging.getLogger("VerseViewSTT")

# Reconnect before GCP's hard 305-second (5 min 5 sec) per-session limit.
# 4 min 45 sec gives a 20-second safety margin.
_SESSION_LIMIT_SECS = 285

# GCP's RecognitionConfig accepts at most 3 alternative language codes
# (4 languages total counting the primary language_code).
_MAX_ALTERNATIVE_LANGUAGES = 3

# Sentence-final punctuation we prefer to chunk on for the interim-flush feature.
# Includes the Devanagari/Indic danda "।" alongside Latin marks because GCP's
# automatic punctuation can emit either depending on the recognised language.
_SENT_PUNCT = ".?!।"


def _carve_stable_chunk(full_text: str, committed_len: int):
    """Carve a readable, word-safe chunk out of a growing interim transcript.

    `full_text` is GCP's cumulative interim transcript for the current utterance
    and `committed_len` is how many leading characters of it have already been
    emitted (as earlier soft-final chunks).  We return ``(chunk, new_committed_len)``
    where `chunk` is the next stable slice to surface and `new_committed_len` is
    the updated commit offset.  Returns ``("", committed_len)`` when there is no
    safe boundary yet (so the caller waits for more audio).

    Boundary preference, to avoid chopping words mid-flow:
      1. The last sentence-punctuation mark that is *followed* by more text — a
         completed clause/sentence is stable and reads cleanly.
      2. Otherwise the last whitespace, holding back the trailing (possibly still
         growing) partial word.
      3. If neither exists (one unbroken token), emit nothing and wait.
    """
    tail = full_text[committed_len:]
    if not tail.strip():
        return "", committed_len

    cut = -1
    # Prefer a punctuation boundary that is confirmed by trailing content.
    for i in range(len(tail) - 1, -1, -1):
        if tail[i] in _SENT_PUNCT and i < len(tail) - 1:
            cut = i + 1
            break

    if cut == -1:
        # No confirmed punctuation — fall back to the last word boundary so we
        # never split a word and we leave the volatile trailing word uncommitted.
        ws = tail.rfind(" ")
        if ws <= 0:
            return "", committed_len
        cut = ws

    chunk = tail[:cut].strip()
    if not chunk:
        return "", committed_len
    return chunk, committed_len + cut


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
          g.  Auth / invalid-config errors → break (fatal); quota errors → 30 s
              back-off; others → reconnect.
    5.  Close gRPC transport.
    6.  teardown_microphone.

    Audio wire format (per StreamingRecognizeRequest after the first)
    -----------------------------------------------------------------
    raw PCM16LE bytes — no base64, no framing.  gRPC handles framing.

    Language modes
    --------------
    Single language → language_code only (e.g. "en-US", "hi-IN", "ml-IN").
    Multi-language  → language_code (primary) + alternative_language_codes.
                      GCP streaming has no universal auto-detect, so true
                      multi-language is wired via the documented
                      alternative_language_codes mechanism: GCP picks which of
                      the supplied languages is being spoken per utterance and
                      reports it back in result.language_code (surfaced in
                      metadata["detected_language"]).

    Config keys
    -----------
    credentials_path            – path to a GCP service account JSON key (required)
    language_code               – primary BCP-47 language code, e.g. "en-US"
    language                    – alias for language_code if language_code is absent
    alternative_language_codes  – optional list of extra BCP-47 codes for
                                  multi-language recognition (max 3)
    rate                        – PCM sample rate (default 16000)
    chunk                       – PyAudio frames_per_buffer (default 4096)
    tag                         – log-prefix string (default "[PRI-GCP]")
    model                       – GCP recognition model (default "latest_long")
    interim_flush_sec           – if > 0, surface stable interim text as readable
                                  soft-final chunks every N seconds during long
                                  uninterrupted speech (default 0 = disabled).
                                  Wired on only for Malayalam by the runtime.
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

        # ── Interim flush (soft-final) ──────────────────────────────────────────
        # When > 0, long uninterrupted speech is surfaced in readable chunks
        # every `interim_flush_sec` seconds instead of waiting for GCP to emit a
        # natural-pause final.  0 disables the feature entirely (original
        # behaviour).  The runtime only enables this for Malayalam on GCP.
        try:
            interim_flush_sec = float(self.config.get("interim_flush_sec") or 0)
        except (TypeError, ValueError):
            interim_flush_sec = 0.0
        flush_enabled = interim_flush_sec > 0

        # Multi-language alternatives — clean to a list of non-empty strings and
        # drop any that duplicate the primary code, then clamp to GCP's max of 3.
        raw_alts = self.config.get("alternative_language_codes") or []
        alt_langs = [
            c.strip()
            for c in raw_alts
            if isinstance(c, str) and c.strip() and c.strip() != language_code
        ]
        if len(alt_langs) > _MAX_ALTERNATIVE_LANGUAGES:
            logger.warning(
                f"⚠️ {tag} GCP accepts at most {_MAX_ALTERNATIVE_LANGUAGES} "
                f"alternative language codes — using the first "
                f"{_MAX_ALTERNATIVE_LANGUAGES} of {alt_langs}"
            )
            alt_langs = alt_langs[:_MAX_ALTERNATIVE_LANGUAGES]

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
        recognition_kwargs = dict(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=rate,
            language_code=language_code,
            enable_automatic_punctuation=True,
            model=model,
        )
        if alt_langs:
            # Real multi-language recognition — GCP detects which of these
            # languages is being spoken per utterance.
            recognition_kwargs["alternative_language_codes"] = alt_langs
        recognition_config = speech.RecognitionConfig(**recognition_kwargs)
        streaming_config = speech.StreamingRecognitionConfig(
            config=recognition_config,
            interim_results=True,
        )

        def _read_audio():
            return stream.read(chunk, exception_on_overflow=False)

        if alt_langs:
            logger.info(
                f"🎤 {tag} Google Cloud STT initialised — multi-language: "
                f"{language_code} (primary) + alternatives {alt_langs} | "
                f"model: {model}"
            )
            logger.info(
                f"ℹ️ {tag} GCP multi-language detects the spoken language per "
                f"utterance from the configured set; detection quality depends on "
                f"GCP model support for alternative_language_codes."
            )
        else:
            logger.info(
                f"🎤 {tag} Google Cloud STT initialised — "
                f"language: {language_code} | model: {model}"
            )

        if flush_enabled:
            logger.info(
                f"⏱️ {tag} Interim flush ON — surfacing stable chunks every "
                f"{interim_flush_sec:g}s during long continuous speech"
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
                    # Per-utterance interim-flush state.  Re-initialised every
                    # session (each reconnect re-defines _recv), so it never
                    # leaks committed text across a reconnect.
                    #   committed_len    – chars of the CURRENT utterance already
                    #                      surfaced as soft-final chunks
                    #   last_commit_time – monotonic time of the last emission,
                    #                      so flushing is paced by interim_flush_sec
                    committed_len = 0
                    last_commit_time = time.monotonic()

                    def _emit(text, final, meta):
                        # extra marks transcript text so the GUI routes it to the
                        # matching pane; finals (incl. soft-finals) are also logged.
                        if final:
                            logger.info(
                                f"📝 {tag} {text}",
                                extra={"vv_transcript": True},
                            )
                        on_transcript(text, final, meta)

                    try:
                        # streaming_recognize is async def — await it to obtain the
                        # async response iterator, then iterate over results normally.
                        responses = await client.streaming_recognize(
                            requests=_audio_gen()
                        )
                        async for response in responses:
                            if stop_event.is_set() or stop_session.is_set():
                                break
                            for idx, result in enumerate(response.results):
                                if not result.alternatives:
                                    continue
                                full     = result.alternatives[0].transcript
                                sentence = full.strip()
                                if not sentence:
                                    continue
                                is_final   = result.is_final
                                confidence = (
                                    result.alternatives[0].confidence
                                    if is_final
                                    else None
                                )
                                # In multi-language mode GCP reports the detected
                                # language per result; fall back to the primary code.
                                detected_language = (
                                    getattr(result, "language_code", "")
                                    or language_code
                                )
                                metadata = {
                                    "engine":            "gcp",
                                    "tag":               tag,
                                    "confidence":        confidence,
                                    "language_code":     language_code,
                                    "detected_language": detected_language,
                                    "raw":               str(result),
                                }

                                if is_final:
                                    # A true final closes the utterance.  If we
                                    # already soft-flushed part of it, emit only
                                    # the not-yet-committed remainder so nothing is
                                    # duplicated; otherwise emit the whole final.
                                    if flush_enabled and committed_len > 0:
                                        remainder = (
                                            full[committed_len:].strip()
                                            if len(full) > committed_len
                                            else ""
                                        )
                                        if remainder:
                                            _emit(remainder, True, metadata)
                                    else:
                                        _emit(sentence, True, metadata)
                                    # Reset for the next utterance.
                                    committed_len = 0
                                    last_commit_time = time.monotonic()
                                    continue

                                # ── Interim result ──────────────────────────────
                                # Always feed the partial to the verse-queue path
                                # (unchanged behaviour).
                                _emit(sentence, False, metadata)

                                # Time-based soft-final flush — only on the primary
                                # hypothesis (idx 0) so secondary low-stability
                                # results never corrupt the commit offset.
                                if (
                                    flush_enabled
                                    and idx == 0
                                    and len(full) > committed_len
                                    and (time.monotonic() - last_commit_time)
                                    >= interim_flush_sec
                                ):
                                    chunk, new_len = _carve_stable_chunk(
                                        full, committed_len
                                    )
                                    if chunk:
                                        soft_meta = dict(metadata)
                                        soft_meta["soft_final"] = True
                                        _emit(chunk, True, soft_meta)
                                        committed_len = new_len
                                        last_commit_time = time.monotonic()
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
                    if "INVALID_ARGUMENT" in err_str:
                        logger.error(
                            f"❌ {tag} GCP rejected the recognition config "
                            f"(INVALID_ARGUMENT). This usually means an unsupported "
                            f"language_code / alternative-language / model "
                            f"combination (e.g. model '{model}' not supporting "
                            f"multi-language). Detail: {exc}"
                        )
                        break   # config error — reconnecting will not help
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
