import asyncio
from abc import ABC, abstractmethod
from typing import Callable, Dict, Any

class STTProvider(ABC):
    """
    Abstract Base Class for all STT providers.
    Isolates engine-specific connection, audio streaming, and transcription logic.
    """
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize with a config dictionary containing engine-specific settings.
        e.g. {'api_key': '...', 'language': 'en', 'rate': 16000, 'chunk': 4096}
        """
        self.config = config

    @abstractmethod
    async def stream_audio(
        self,
        mic_index: int,
        stop_event: asyncio.Event,
        on_transcript: Callable[[str, bool, dict], None]
    ):
        """
        Connects to the microphone and STT backend.
        
        Args:
            mic_index: The PyAudio device index to read from.
            stop_event: An asyncio.Event indicating when to stop the stream.
            on_transcript: Callback fired when a transcript is received.
                           Signature: (sentence: str, is_final: bool, metadata: dict)
        """
        pass
