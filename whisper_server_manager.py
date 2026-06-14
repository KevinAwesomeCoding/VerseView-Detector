import subprocess
import sys
import time
import os
import threading
import logging
import requests

logger = logging.getLogger("VerseViewSTT")

WHISPER_PORT = 8000   # faster-whisper-server default
WHISPER_ENDPOINT_BASE = f"http://127.0.0.1:{WHISPER_PORT}"
WHISPER_HEALTH_URL = f"{WHISPER_ENDPOINT_BASE}/health"
WHISPER_TRANSCRIBE_URL = f"{WHISPER_ENDPOINT_BASE}/v1/audio/transcriptions"

_server_process = None
_server_lock = threading.Lock()
_current_model = None


def _get_model_for_language(language: str) -> str:
    """
    Map session language to the appropriate faster-whisper model.
    
    Args:
        language: Two-letter or region-qualified language code (e.g., "en", "ml", "ml-IN")
    
    Returns:
        Model name: "base.en" for English, "base" for multilingual languages, default "base"
    """
    # Normalize: extract language code from region-qualified codes (e.g., "ml-IN" → "ml")
    lang_code = (language or "en").lower().split("-")[0].strip()
    
    # English gets the optimized English model
    if lang_code == "en":
        return "base.en"
    
    # Multilingual languages get the base (multilingual) model
    multilingual_langs = {"ml", "hi", "ta", "te", "kn", "mr", "multi"}
    if lang_code in multilingual_langs:
        return "base"
    
    # Safe fallback for unknown languages
    return "base"


def _is_server_running() -> bool:
    """Check if the Whisper server is responding to health checks."""
    try:
        r = requests.get(WHISPER_HEALTH_URL, timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def _install_faster_whisper():
    """Install faster-whisper-server via pip if not already installed."""
    logger.info("📦 Installing faster-whisper-server (first time setup)...")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-q", 
             "faster-whisper", "uvicorn", "fastapi", "python-multipart"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info("✅ faster-whisper-server installed.")
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Failed to install faster-whisper-server: {e}")
        raise


def _predownload_model(model: str):
    """Pre-download the Whisper model so the server starts instantly."""
    logger.info(f"📥 Pre-downloading Whisper model '{model}' (this may take a minute)...")
    try:
        from faster_whisper import WhisperModel
        WhisperModel(model, device="cpu", compute_type="int8")
        logger.info(f"✅ Model '{model}' ready.")
    except Exception as e:
        logger.warning(f"⚠️ Model pre-download failed: {e} — server will download on first request")


def _start_server(model: str) -> bool:
    """
    Start the faster-whisper-server as a background subprocess.
    
    Args:
        model: Whisper model name (e.g., "base.en", "base")
    
    Returns:
        True if server started and is responding; False if startup failed.
    """
    global _server_process, _current_model
    
    _predownload_model(model)
    
    logger.info(f"🚀 Starting local Whisper server (model={model}) on port {WHISPER_PORT}...")
    
    cmd = [
        sys.executable, "-m", "faster_whisper_server",
        model,               # e.g. "base.en" or "base"
    ]
    
    # Windows: suppress console window
    kwargs = {}
    if sys.platform.startswith("win"):
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    
    try:
        _server_process = subprocess.Popen(
            cmd,
            stdout=None,
            stderr=None,
            **kwargs,
        )
    except Exception as e:
        logger.error(f"❌ Failed to start Whisper server subprocess: {e}")
        return False
    
    # Wait up to 60 seconds for the server to come online (model download on first run)
    for attempt in range(60):
        time.sleep(1.0)
        if _is_server_running():
            _current_model = model
            logger.info(f"✅ Local Whisper server ready at {WHISPER_TRANSCRIBE_URL}")
            return True
    
    logger.error("❌ Local Whisper server did not start in time.")
    return False


def ensure_whisper_server(language: str = "en") -> str:
    """
    Ensure the faster-whisper-server is running with the appropriate model for the given language.
    
    This function:
    1. Checks if the server is already running with the correct model
    2. If not running, installs faster-whisper-server if needed
    3. Starts the server with the language-appropriate model
    4. Waits for the server to become ready
    
    Args:
        language: Session language code (e.g., "en", "ml", "hi", "multi")
    
    Returns:
        The transcribe endpoint URL if successful.
    
    Raises:
        RuntimeError: If the server fails to start or becomes unavailable.
    
    Usage:
        Call this inside build_stt_provider() when engine_name == "local_whisper":
        
        endpoint = ensure_whisper_server(language=DEEPGRAM_LANGUAGE)
        return LocalWhisperProvider({"endpoint": endpoint, ...})
    """
    global _server_process, _current_model
    
    with _server_lock:
        target_model = _get_model_for_language(language)
        
        # Server is already running with the correct model — reuse it
        if _is_server_running() and _current_model == target_model:
            logger.info(f"✅ Local Whisper server already running (model={target_model}) at {WHISPER_TRANSCRIBE_URL}")
            return WHISPER_TRANSCRIBE_URL
        
        # Server is running but with a different model — stop it and restart
        if _is_server_running() and _current_model != target_model:
            logger.info(f"🔄 Model mismatch: running={_current_model}, needed={target_model}. Restarting...")
            stop_whisper_server()
        
        # Try to install if not already present
        try:
            import faster_whisper  # noqa: F401
        except ImportError:
            _install_faster_whisper()
        
        # Start the server with the correct model
        if not _start_server(target_model):
            raise RuntimeError(
                f"Local Whisper server failed to start with model '{target_model}'. "
                "Check logs and ensure port 8080 is available."
            )
        
        return WHISPER_TRANSCRIBE_URL


def stop_whisper_server():
    """
    Stop the faster-whisper-server subprocess and clean up resources.
    
    Safe to call even if the server is not running.
    """
    global _server_process, _current_model
    
    if _server_process and _server_process.poll() is None:
        logger.info("🛑 Stopping local Whisper server...")
        try:
            _server_process.terminate()
            _server_process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            logger.warning("⚠️ Whisper server did not stop gracefully; forcing kill...")
            _server_process.kill()
        except Exception as e:
            logger.warning(f"⚠️ Error stopping Whisper server: {e}")
        finally:
            _server_process = None
            _current_model = None
