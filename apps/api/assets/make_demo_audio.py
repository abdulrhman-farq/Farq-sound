"""Generate placeholder audio assets for the demo catalog.

Pure synthesized tones — these stand in for the real isolated vocals
and instrumental tracks until licensed material is loaded via the
admin intake flow. Outputs:

  apps/api/storage/songs/<slug>/vocals.wav        (synthetic vocal layer)
  apps/api/storage/songs/<slug>/instrumental.wav  (synthetic instrumental)
  apps/web/public/samples/preview-<slug>.mp3      (30s teaser, mixed)

Run from the apps/api directory:
    python assets/make_demo_audio.py
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf

SR = 44_100


def synth_vocal_layer(duration_s: float, fundamental: float = 220.0) -> np.ndarray:
    """A breathy sustained tone that imitates a vocal sustain.

    Stack of sine partials with a slow vibrato — no lyrics, no melody.
    """
    t = np.arange(int(SR * duration_s)) / SR
    vibrato = 1.0 + 0.015 * np.sin(2 * np.pi * 5.5 * t)
    base = np.sin(2 * np.pi * fundamental * vibrato * t)
    partial = 0.5 * np.sin(2 * np.pi * fundamental * 2 * vibrato * t)
    partial2 = 0.25 * np.sin(2 * np.pi * fundamental * 3 * vibrato * t)
    sig = (base + partial + partial2) / 1.75
    # ADSR-ish envelope so it sounds like phrases.
    phrase_len = int(2.4 * SR)
    env = np.zeros_like(t)
    for start in range(0, len(t), phrase_len):
        end = min(start + phrase_len, len(t))
        n = end - start
        seg = np.ones(n)
        attack = int(0.15 * SR)
        release = int(0.4 * SR)
        if n > attack + release:
            seg[:attack] = np.linspace(0, 1, attack)
            seg[-release:] = np.linspace(1, 0, release)
        env[start:end] = seg
    return (sig * env * 0.35).astype(np.float32)


def synth_instrumental(duration_s: float, root: float = 110.0) -> np.ndarray:
    """A simple instrumental bed — sustained pad chord at a constant tempo.

    Triadic chord (root + maj third + fifth) with a slow LFO on amplitude
    to mimic phrasing.
    """
    t = np.arange(int(SR * duration_s)) / SR
    # Major triad: root, +4 semitones, +7 semitones
    intervals = [1.0, 2 ** (4 / 12), 2 ** (7 / 12)]
    chord = np.zeros_like(t)
    for ratio in intervals:
        chord += np.sin(2 * np.pi * root * ratio * t)
        chord += 0.3 * np.sin(2 * np.pi * root * ratio * 2 * t)
    chord /= len(intervals) * 1.3
    # Gentle amplitude wobble + steady kick on the 1.
    bpm = 92
    kick_period = 60.0 / bpm
    kick_phase = (t % kick_period) / kick_period
    kick = 0.4 * np.exp(-30 * kick_phase) * np.sin(2 * np.pi * 60 * t)
    pad_env = 0.85 + 0.15 * np.sin(2 * np.pi * 0.5 * t)
    sig = chord * pad_env * 0.3 + kick * 0.5
    return sig.astype(np.float32)


def write_song(out_dir: Path, vocals_freq: float, inst_root: float) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    duration = 180.0
    vocals = synth_vocal_layer(duration, fundamental=vocals_freq)
    inst = synth_instrumental(duration, root=inst_root)
    sf.write(out_dir / "vocals.wav", vocals, SR, subtype="PCM_16")
    sf.write(out_dir / "instrumental.wav", inst, SR, subtype="PCM_16")


def write_preview(song_dir: Path, public_samples: Path, slug: str) -> None:
    public_samples.mkdir(parents=True, exist_ok=True)
    mp3 = public_samples / f"preview-{slug}.mp3"
    # 30-second preview = mix of vocals + instrumental, normalized.
    cmd = [
        "ffmpeg", "-y",
        "-i", str(song_dir / "vocals.wav"),
        "-i", str(song_dir / "instrumental.wav"),
        "-filter_complex",
        "[0:a][1:a]amix=inputs=2:duration=longest,atrim=0:30,"
        "loudnorm=I=-16:TP=-1.5:LRA=11",
        "-b:a", "192k",
        str(mp3),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main() -> None:
    storage_root = Path(__file__).resolve().parents[1] / "storage" / "songs"
    public_root = Path(__file__).resolve().parents[3] / "apps" / "web" / "public" / "samples"

    songs = [
        # (slug, vocals fundamental Hz, instrumental root Hz)
        ("demo-classic-1", 240.0, 110.0),  # higher voice, A minor-ish
        ("demo-classic-2", 196.0, 130.81), # mid voice, C
        ("demo-modern-1",  293.66, 146.83),# bright, D
    ]

    for slug, vfreq, iroot in songs:
        d = storage_root / slug
        write_song(d, vocals_freq=vfreq, inst_root=iroot)
        write_preview(d, public_root, slug)
        print(f"  ✓ {slug} → vocals + instrumental + preview")

    print(f"\nstorage root: {storage_root}")
    print(f"public previews: {public_root}")


if __name__ == "__main__":
    main()
