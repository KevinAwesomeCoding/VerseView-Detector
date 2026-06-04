"""
Shared utilities for the STT provider package.

    open_microphone(mic_index, rate, chunk)
        Open a PyAudio input stream. Returns (audio, stream).
        Raises RuntimeError with a user-readable message on failure.

    teardown_microphone(audio, stream, chunk, rate)
        Safe stream + interface teardown. Handles CoreAudio re-entrancy on macOS
        (abort_stream instead of stop_stream) and lets an in-flight
        run_in_executor read() return before touching PortAudio.

    run_placeholder_loop(stop_event, interval)
        Async wait loop for engines not yet implemented. Holds the task alive
        while respecting stop_event and CancelledError.

    validate_config(config, required)
        Raise ValueError listing every required key that is missing or empty.
"""

import asyncio
import logging
import sys

logger = logging.getLogger("VerseViewSTT")


def validate_config(config: dict, required: list) -> None:
    """Raise ValueError listing every required key that is missing or empty."""
    missing = []
    for key in required:
        val = config.get(key)
        if val is None or (isinstance(val, str) and not val.strip()):
            missing.append(key)
    if missing:
        raise ValueError(f"Missing required config keys: {', '.join(missing)}")


def open_microphone(mic_index: int, rate: int, chunk: int):
    """Open a PyAudio input stream.

    Returns (audio, stream) on success.
    Raises RuntimeError with a descriptive message on any failure so callers
    can log and bail without boilerplate.
    """
    import pyaudio

    audio = pyaudio.PyAudio()
    try:
        mic_info = audio.get_device_info_by_index(mic_index)
        logger.info(f"Using: [{mic_index}] {mic_info['name']}")
        if "stereo mix" in mic_info["name"].lower():
            logger.warning(
                "⚠️ Stereo Mix selected — ALL desktop audio will be captured. "
                "Non-church audio may trigger false detections."
            )
        stream = audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=rate,
            input=True,
            input_device_index=mic_index,
            frames_per_buffer=chunk,
        )
        logger.info("Microphone opened")
        return audio, stream
    except Exception as exc:
        try:
            audio.terminate()
        except Exception:
            pass
        raise RuntimeError(f"Microphone error: {exc}") from exc


def teardown_microphone(audio, stream, chunk: int, rate: int) -> None:
    """Safely close a PyAudio stream and terminate the interface.

    On macOS/CoreAudio, abort_stream() is used instead of stop_stream() to
    avoid SIGSEGV crashes when a blocking read() is still in-flight inside a
    run_in_executor thread. A short sleep before each PortAudio call lets the
    OS callback thread settle.
    """
    import time as _t

    _chunk_secs = chunk / max(rate, 1)
    _t.sleep(_chunk_secs + 0.05)   # let in-flight executor read() return

    if stream:
        try:
            if sys.platform == "darwin":
                stream.abort_stream()
            else:
                stream.stop_stream()
        except Exception:
            pass
        _t.sleep(0.05)
        try:
            stream.close()
        except Exception:
            pass

    _t.sleep(0.1)
    try:
        audio.terminate()
    except Exception:
        pass


async def run_placeholder_loop(stop_event: asyncio.Event, interval: float = 0.25) -> None:
    """Hold a provider task alive for engines not yet implemented.

    Wakes every *interval* seconds to check stop_event so shutdown is prompt.
    Exits cleanly on CancelledError.
    """
    try:
        while not stop_event.is_set():
            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        pass
