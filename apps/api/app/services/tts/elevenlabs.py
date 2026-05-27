"""ElevenLabs Multilingual v2 TTS provider.

The voice cloning step (uploading singer samples and getting a
`voice_id`) is done **once per song** during catalog onboarding via the
admin intake flow. At render time we only call the synthesis endpoint
with a pre-existing voice id.

API docs: https://elevenlabs.io/docs/api-reference/text-to-speech
"""
from __future__ import annotations

from pathlib import Path

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .base import (
    TTSProvider,
    TTSRequest,
    TTSResult,
    VoiceCloneRequest,
    VoiceCloneResult,
)


class ElevenLabsProvider(TTSProvider):
    name = "elevenlabs"
    supports_cloning = True
    sample_rate = 44_100
    base_url = "https://api.elevenlabs.io/v1"

    def __init__(self, api_key: str, model_id: str) -> None:
        self.api_key = api_key
        self.model_id = model_id

    @retry(
        retry=retry_if_exception_type(httpx.HTTPError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def synthesize(self, request: TTSRequest, out_path: Path) -> TTSResult:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        url = f"{self.base_url}/text-to-speech/{request.voice_model_id}"
        # Build text with phonetic hint applied as SSML-style override.
        text = request.text_ar
        if request.phonetic_hint:
            # ElevenLabs accepts inline pronunciation hints via the
            # `pronunciation_dictionary_locators` field; for the MVP we
            # pre-format the text per the hint, which is good enough for
            # diacritics-driven Arabic pronunciation.
            text = request.phonetic_hint
        payload = {
            "text": text,
            "model_id": self.model_id,
            "voice_settings": {
                "stability": 0.55,
                "similarity_boost": 0.85,
                "style": 0.35,
                "use_speaker_boost": True,
            },
            "output_format": "pcm_44100",
        }
        headers = {
            "xi-api-key": self.api_key,
            "accept": "audio/pcm",
        }
        with httpx.Client(timeout=60) as client:
            r = client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            pcm = r.content

        # Wrap raw 16-bit little-endian PCM in a WAV container.
        import numpy as np
        import soundfile as sf

        samples = np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0
        sf.write(out_path, samples, self.sample_rate, subtype="PCM_16")
        duration_ms = int(1000 * len(samples) / self.sample_rate)
        return TTSResult(
            audio_path=out_path,
            sample_rate=self.sample_rate,
            duration_ms=duration_ms,
        )

    @retry(
        retry=retry_if_exception_type(httpx.HTTPError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def clone_voice(self, request: VoiceCloneRequest) -> VoiceCloneResult:
        """Instant Voice Clone via POST /v1/voices/add (multipart)."""
        url = f"{self.base_url}/voices/add"
        files = [
            ("files", (p.name, open(p, "rb"), "audio/wav"))
            for p in request.sample_paths
        ]
        data: dict[str, str] = {"name": request.name}
        if request.description:
            data["description"] = request.description
        headers = {"xi-api-key": self.api_key}
        try:
            with httpx.Client(timeout=120) as client:
                r = client.post(url, data=data, files=files, headers=headers)
                r.raise_for_status()
                body = r.json()
        finally:
            for _, (_, fh, _) in files:
                fh.close()
        return VoiceCloneResult(voice_id=body["voice_id"], name=request.name)
