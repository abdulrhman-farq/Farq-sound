"""Abstract TTS provider interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TTSRequest:
    voice_model_id: str
    text_ar: str
    target_duration_ms: int
    phonetic_hint: str | None = None
    prosody_note: str | None = None


@dataclass
class TTSResult:
    audio_path: Path
    sample_rate: int
    duration_ms: int


class TTSProvider(ABC):
    name: str = "abstract"

    @abstractmethod
    def synthesize(self, request: TTSRequest, out_path: Path) -> TTSResult:
        """Render `text_ar` in `voice_model_id`'s voice and write WAV to disk."""
