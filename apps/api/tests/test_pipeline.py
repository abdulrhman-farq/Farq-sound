"""Smoke tests for the audio pipeline — pure-Python stages only.

These tests exercise the parts of the render chain that don't shell out
to ffmpeg, so they run in CI without system audio binaries installed.
The ffmpeg-backed mixdown/master stages are covered separately in
integration tests that require the docker-compose stack.
"""
from pathlib import Path

import numpy as np
import soundfile as sf

from app.services.pipeline import (
    pitch_and_time_match,
    slice_reference,
    splice_into_vocals,
)
from app.services.tts import VoiceCloneRequest, TTSRequest
from app.services.tts.mock import MockTTSProvider


SR = 44_100


def _make_tone(path: Path, duration_s: float, freq: float = 220.0) -> None:
    t = np.arange(int(SR * duration_s)) / SR
    sig = 0.2 * np.sin(2 * np.pi * freq * t)
    sf.write(path, sig.astype(np.float32), SR)


def test_mock_tts_writes_wav_of_target_duration(tmp_path: Path) -> None:
    provider = MockTTSProvider()
    out = tmp_path / "tts.wav"
    result = provider.synthesize(
        TTSRequest(
            voice_model_id="mock",
            text_ar="placeholder",
            target_duration_ms=1500,
        ),
        out_path=out,
    )
    assert result.audio_path.exists()
    assert abs(result.duration_ms - 1500) < 10
    audio, sr = sf.read(out)
    assert sr == 44_100
    assert abs(len(audio) / sr - 1.5) < 0.01


def test_slice_reference_extracts_window(tmp_path: Path) -> None:
    src = tmp_path / "src.wav"
    _make_tone(src, duration_s=3.0)
    out = tmp_path / "slice.wav"
    slice_reference(src, start_ms=500, end_ms=1500, out_path=out)
    audio, sr = sf.read(out)
    assert sr == SR
    assert abs(len(audio) / sr - 1.0) < 0.02


def test_pitch_match_hits_target_duration(tmp_path: Path) -> None:
    gen = tmp_path / "gen.wav"
    ref = tmp_path / "ref.wav"
    _make_tone(gen, duration_s=0.8, freq=300.0)
    _make_tone(ref, duration_s=1.2, freq=200.0)
    out = tmp_path / "matched.wav"
    pitch_and_time_match(
        generated_path=gen,
        reference_path=ref,
        target_duration_ms=1200,
        out_path=out,
    )
    audio, sr = sf.read(out)
    target_samples = int(1.2 * sr)
    assert len(audio) == target_samples


def test_splice_replaces_region_with_crossfade(tmp_path: Path) -> None:
    vocals = tmp_path / "vocals.wav"
    _make_tone(vocals, duration_s=3.0, freq=150.0)
    seg = tmp_path / "seg.wav"
    _make_tone(seg, duration_s=0.5, freq=600.0)

    out = tmp_path / "spliced.wav"
    splice_into_vocals(
        isolated_vocals_path=vocals,
        replacements=[(1000, 1500, seg)],
        out_path=out,
    )

    audio, sr = sf.read(out)
    # Length is unchanged.
    assert len(audio) == int(3.0 * sr)
    # The middle 500 ms should be dominated by the higher-frequency
    # replacement signal.
    mid = audio[int(1.1 * sr) : int(1.4 * sr)]
    edge = audio[int(0.1 * sr) : int(0.4 * sr)]
    # Use spectral energy ratio between bands as a coarse check.
    def hf_energy(x: np.ndarray) -> float:
        spec = np.abs(np.fft.rfft(x))
        freqs = np.fft.rfftfreq(len(x), 1 / sr)
        return float(spec[freqs > 400].sum())

    assert hf_energy(mid) > hf_energy(edge) * 2


def test_mock_clone_voice_is_deterministic(tmp_path: Path) -> None:
    provider = MockTTSProvider()
    sample = tmp_path / "sample.wav"
    _make_tone(sample, duration_s=0.5)
    r1 = provider.clone_voice(
        VoiceCloneRequest(name="farq-test-1", sample_paths=[sample])
    )
    r2 = provider.clone_voice(
        VoiceCloneRequest(name="farq-test-1", sample_paths=[sample])
    )
    r3 = provider.clone_voice(
        VoiceCloneRequest(name="farq-test-2", sample_paths=[sample])
    )
    assert r1.provider == "mock"
    assert r1.voice_id.startswith("mock_")
    assert r1.voice_id == r2.voice_id, "same name => same id"
    assert r1.voice_id != r3.voice_id, "different name => different id"


def test_pipeline_chain_end_to_end_pure_python(tmp_path: Path) -> None:
    """Run TTS → slice → match → splice without ffmpeg."""
    # Stand in for `isolated_vocals_url` from the song.
    vocals = tmp_path / "vocals.wav"
    _make_tone(vocals, duration_s=4.0, freq=180.0)

    segments = [
        {"role": "groom", "sequence_index": 1, "start_ms": 1000, "end_ms": 1600},
        {"role": "bride", "sequence_index": 2, "start_ms": 2200, "end_ms": 2700},
    ]
    names = {"groom": "placeholder1", "bride": "placeholder2"}

    provider = MockTTSProvider()
    matched_paths = []
    for seg in segments:
        target_ms = seg["end_ms"] - seg["start_ms"]
        tts_out = tmp_path / f"tts-{seg['sequence_index']}.wav"
        provider.synthesize(
            TTSRequest(
                voice_model_id="mock",
                text_ar=names[seg["role"]],
                target_duration_ms=target_ms,
            ),
            out_path=tts_out,
        )
        ref = tmp_path / f"ref-{seg['sequence_index']}.wav"
        slice_reference(vocals, seg["start_ms"], seg["end_ms"], ref)
        matched = tmp_path / f"matched-{seg['sequence_index']}.wav"
        pitch_and_time_match(tts_out, ref, target_ms, matched)
        matched_paths.append((seg["start_ms"], seg["end_ms"], matched))

    spliced = tmp_path / "spliced.wav"
    splice_into_vocals(vocals, matched_paths, spliced)
    assert spliced.exists()
    audio, sr = sf.read(spliced)
    assert len(audio) == int(4.0 * sr)
