"""TTS / voice clone provider abstraction.

`get_tts_provider()` returns the live provider when an API key is
present, otherwise a deterministic mock that writes silent WAVs of the
requested duration. All downstream pipeline code targets this interface,
so swapping ElevenLabs for RVC v2 later is a one-file change.
"""
from __future__ import annotations

from app.config import get_settings

from .base import TTSProvider, TTSRequest, TTSResult
from .elevenlabs import ElevenLabsProvider
from .mock import MockTTSProvider


def get_tts_provider() -> TTSProvider:
    settings = get_settings()
    if settings.tts_mode == "live":
        return ElevenLabsProvider(
            api_key=settings.elevenlabs_api_key,
            model_id=settings.elevenlabs_model_id,
        )
    return MockTTSProvider()


__all__ = [
    "TTSProvider",
    "TTSRequest",
    "TTSResult",
    "get_tts_provider",
]
