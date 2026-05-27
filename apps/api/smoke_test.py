"""End-to-end smoke test — proves the stack produces a real MP3.

Bypasses Supabase + Celery (those need credentials and a broker we
already verified separately) and drives the pipeline directly.

Run from apps/api/:
    python smoke_test.py
"""
from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

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

HERE = Path(__file__).resolve().parent
SONG_DIR = HERE / "storage" / "songs" / "demo-classic-1"
OUT_DIR = HERE / "storage" / "smoke-output"


def ffprobe(p: Path) -> dict:
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_streams", "-of", "default=nw=1", str(p)],
        text=True,
    )
    return dict(line.split("=", 1) for line in out.splitlines() if "=" in line)


def main() -> None:
    if not (SONG_DIR / "vocals.wav").exists():
        print("✗ demo audio missing — run: python assets/make_demo_audio.py")
        return
    if not shutil.which("ffmpeg"):
        print("✗ ffmpeg not installed")
        return

    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True)

    print("=" * 60)
    print(" Farq Sound — end-to-end pipeline smoke test")
    print("=" * 60)

    # A realistic order: groom + bride, 2 segments.
    segments = [
        {"role": "groom", "start_ms": 22_000, "end_ms": 24_500, "seq": 1},
        {"role": "bride", "start_ms": 41_000, "end_ms": 43_200, "seq": 2},
    ]
    names = {"groom": "محمد", "bride": "نورة"}

    t0 = time.time()
    tts = MockTTSProvider()
    matched = []

    # Stage 1+2 — TTS, then slice the reference + pitch-match.
    for seg in segments:
        target_ms = seg["end_ms"] - seg["start_ms"]
        tts_out = OUT_DIR / f"tts-{seg['seq']}.wav"
        tts.synthesize(
            TTSRequest(
                voice_model_id="mock",
                text_ar=names[seg["role"]],
                target_duration_ms=target_ms,
            ),
            out_path=tts_out,
        )

        ref = OUT_DIR / f"ref-{seg['seq']}.wav"
        slice_reference(
            SONG_DIR / "vocals.wav", seg["start_ms"], seg["end_ms"], ref
        )

        matched_path = OUT_DIR / f"matched-{seg['seq']}.wav"
        pitch_and_time_match(tts_out, ref, target_ms, matched_path)
        matched.append((seg["start_ms"], seg["end_ms"], matched_path))
        print(f"  [stage 1+2] {seg['role']:8s} ({names[seg['role']]}) {target_ms}ms ✓")

    t_pitch = time.time()
    print(f"  → stages 1-2 took {t_pitch - t0:.1f}s")

    # Stage 3 — splice
    spliced = OUT_DIR / "spliced-vocals.wav"
    splice_into_vocals(SONG_DIR / "vocals.wav", matched, spliced)
    print(f"  [stage 3 ] splice w/ 30ms crossfade ✓")

    # Stage 4 — mixdown
    mixed = OUT_DIR / "mix.wav"
    mixdown(spliced, SONG_DIR / "instrumental.wav", mixed)
    print(f"  [stage 4 ] mixdown + LUFS -14 ✓")

    # Stage 5 — master to MP3 + preview watermark
    final = OUT_DIR / "final.mp3"
    master_to_mp3(
        mixed, final,
        bitrate="320k",
        title=f"Demo Classic 1 — {names['groom']} و {names['bride']}",
        artist="Farq Sound",
    )

    watermark = HERE / "assets" / "watermark.wav"
    preview = OUT_DIR / "preview.mp3"
    add_preview_watermark(final, watermark, preview)
    print(f"  [stage 5 ] master + watermark ✓")

    elapsed = time.time() - t0

    final_info = ffprobe(final)
    preview_info = ffprobe(preview)
    print()
    print("=" * 60)
    print(" RESULT")
    print("=" * 60)
    print(f"  total time         : {elapsed:.1f}s")
    print(f"  final MP3          : {final}")
    print(f"    codec            : {final_info.get('codec_name')}")
    print(f"    sample rate      : {final_info.get('sample_rate')} Hz")
    print(f"    bitrate          : {int(final_info.get('bit_rate', 0)) // 1000} kbps")
    print(f"    duration         : {float(final_info.get('duration', 0)):.1f}s")
    print(f"    size             : {final.stat().st_size // 1024} KB")
    print(f"  preview (watermark): {preview.stat().st_size // 1024} KB")
    print()
    print("  ✓ stack works end-to-end. Listen at:")
    print(f"    {final}")
    print(f"    {preview}")


if __name__ == "__main__":
    main()
