"""Deterministic mock TTS provider — emits a silent WAV of target duration.

Used when ELEVENLABS_API_KEY is empty so the full pipeline can run in dev
and CI without burning credits or needing network access.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import soundfile as sf

from .base import (
    TTSProvider,
    TTSRequest,
    TTSResult,
    VoiceCloneRequest,
    VoiceCloneResult,
)


class MockTTSProvider(TTSProvider):
    name = "mock"
    supports_cloning = True
    sample_rate = 44_100

    def clone_voice(self, request: VoiceCloneRequest) -> VoiceCloneResult:
        # Deterministic id derived from the voice name so the same input
        # yields the same id across calls in a dev workflow / tests.
        digest = hashlib.sha1(request.name.encode("utf-8")).hexdigest()[:20]
        return VoiceCloneResult(
            voice_id=f"mock_{digest}",
            provider="mock",
            name=request.name,
        )

    def synthesize(self, request: TTSRequest, out_path: Path) -> TTSResult:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        # A faint sine pulse so the audio is technically audible in dev,
        # but quiet enough that the placeholder doesn't fool anyone.
        duration_s = max(request.target_duration_ms, 100) / 1000.0
        n = int(duration_s * self.sample_rate)
        t = np.arange(n) / self.sample_rate
        envelope = np.minimum(t / 0.05, 1.0) * np.minimum(
            (duration_s - t) / 0.05, 1.0
        )
        envelope = np.clip(envelope, 0.0, 1.0)
        signal = 0.01 * envelope * np.sin(2 * np.pi * 220.0 * t)
        sf.write(out_path, signal.astype(np.float32), self.sample_rate)
        return TTSResult(
            audio_path=out_path,
            sample_rate=self.sample_rate,
            duration_ms=int(duration_s * 1000),
        )
