"""Full pipeline integration test.

Runs the complete 5-stage render chain on the synthesized demo audio
that `assets/make_demo_audio.py` produces. Verifies that:

  1. Every stage produces an output file.
  2. The final MP3 exists, is non-trivial in size, and is a valid
     MPEG audio stream as far as `ffprobe` can tell.

Skipped automatically when ffmpeg / rubberband / demo assets are absent.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

DEMO_ROOT = Path(__file__).resolve().parents[1] / "storage" / "songs" / "demo-classic-1"
HAS_FFMPEG = shutil.which("ffmpeg") is not None
HAS_DEMO = (DEMO_ROOT / "vocals.wav").exists() and (DEMO_ROOT / "instrumental.wav").exists()

pytestmark = pytest.mark.skipif(
    not (HAS_FFMPEG and HAS_DEMO),
    reason="Requires ffmpeg + demo audio (run assets/make_demo_audio.py)",
)


def _ffprobe(path: Path) -> dict:
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_streams", "-of", "default=nw=1",
         str(path)],
        text=True,
    )
    info: dict[str, str] = {}
    for line in out.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            info[k] = v
    return info


def test_full_render_chain_produces_mp3(tmp_path: Path) -> None:
    from app.services.pipeline import (
        add_preview_watermark,
        master_to_mp3,
        mixdown,
        pitch_and_time_match,
        slice_reference,
        splice_into_vocals,
    )
    from app.services.tts import TTSRequest
    from app.services.tts.mock import MockTTSProvider

    vocals_src = DEMO_ROOT / "vocals.wav"
    inst_src = DEMO_ROOT / "instrumental.wav"

    # Two name segments inside the 180-second demo track.
    segments = [
        {"role": "groom", "sequence_index": 1, "start_ms": 22_000, "end_ms": 24_500},
        {"role": "bride", "sequence_index": 2, "start_ms": 41_000, "end_ms": 43_200},
    ]
    names = {"groom": "أحمد", "bride": "سارة"}

    work = tmp_path / "order-integration"
    work.mkdir()

    # Stage 1 — TTS
    tts = MockTTSProvider()
    tts_paths = []
    for seg in segments:
        target_ms = seg["end_ms"] - seg["start_ms"]
        out = work / f"tts-{seg['sequence_index']}.wav"
        tts.synthesize(
            TTSRequest(
                voice_model_id="mock",
                text_ar=names[seg["role"]],
                target_duration_ms=target_ms,
            ),
            out_path=out,
        )
        assert out.exists() and out.stat().st_size > 1000
        tts_paths.append(out)

    # Stage 2 — pitch & time match against sliced reference
    matched = []
    for seg, tts_path in zip(segments, tts_paths, strict=True):
        ref = work / f"ref-{seg['sequence_index']}.wav"
        slice_reference(vocals_src, seg["start_ms"], seg["end_ms"], ref)
        assert ref.exists()
        out = work / f"matched-{seg['sequence_index']}.wav"
        pitch_and_time_match(
            generated_path=tts_path,
            reference_path=ref,
            target_duration_ms=seg["end_ms"] - seg["start_ms"],
            out_path=out,
        )
        assert out.exists()
        matched.append((seg["start_ms"], seg["end_ms"], out))

    # Stage 3 — splice
    spliced = work / "spliced-vocals.wav"
    splice_into_vocals(
        isolated_vocals_path=vocals_src,
        replacements=matched,
        out_path=spliced,
    )
    assert spliced.exists() and spliced.stat().st_size > 10_000_000  # ~ raw WAV

    # Stage 4 — mixdown via ffmpeg
    mixed = work / "mix.wav"
    mixdown(vocals_path=spliced, instrumental_path=inst_src, out_path=mixed)
    assert mixed.exists()

    # Stage 5 — master to MP3
    final_mp3 = work / "final.mp3"
    master_to_mp3(
        wav_path=mixed,
        out_path=final_mp3,
        bitrate="192k",
        title="Demo — أحمد و سارة",
        artist="Farq Sound Test",
    )
    assert final_mp3.exists()
    assert final_mp3.stat().st_size > 1_000_000  # ~ at least 1 MB for 3 min @ 192k

    info = _ffprobe(final_mp3)
    assert info.get("codec_name") == "mp3"
    assert int(info.get("sample_rate", "0")) >= 44_100

    # Preview watermark overlay shouldn't break the file.
    watermark = Path(__file__).resolve().parents[1] / "assets" / "watermark.wav"
    if watermark.exists():
        preview = work / "preview.mp3"
        add_preview_watermark(final_mp3, watermark, preview)
        assert preview.exists()
        assert _ffprobe(preview).get("codec_name") == "mp3"
