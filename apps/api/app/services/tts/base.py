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


@dataclass
class VoiceCloneRequest:
    name: str
    sample_paths: list[Path]
    description: str | None = None


@dataclass
class VoiceCloneResult:
    voice_id: str
    provider: str
    name: str | None = None


class TTSProvider(ABC):
    name: str = "abstract"
    supports_cloning: bool = False

    @abstractmethod
    def synthesize(self, request: TTSRequest, out_path: Path) -> TTSResult:
        """Render `text_ar` in `voice_model_id`'s voice and write WAV to disk."""

    def clone_voice(self, request: VoiceCloneRequest) -> VoiceCloneResult:
        """Create a cloned voice from samples. Override in providers that
        actually support it (set `supports_cloning = True`)."""
        raise NotImplementedError(
            f"Provider {self.name!r} does not support voice cloning."
        )
