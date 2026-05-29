"""Generate placeholder zaffa-style audio for the demo catalog.

All audio is pure DSP synthesis — no copyrighted material.

Each track uses:
- Hijaz maqam (the most common Khaleeji wedding-music scale)
- Daff-like frame-drum percussion at 96 BPM
- An ney-like sustained voice layer with silences where name segments go

Outputs:
  apps/api/storage/songs/<slug>/vocals.wav        (synthetic vocal layer)
  apps/api/storage/songs/<slug>/instrumental.wav  (daff + oud-like bed)
  apps/web/public/samples/preview-<slug>.mp3      (30s mixed preview)

Run from apps/api/:
    python assets/make_demo_audio.py
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf

SR = 44_100


# --- Maqam Hijaz (D Hijaz): D Eb F# G A Bb C# D ----------------------
# Intervals in semitones from the root.
HIJAZ_STEPS = [0, 1, 4, 5, 7, 8, 11, 12]


def hz(root_hz: float, scale_step: int) -> float:
    """Return the frequency for `scale_step` of Hijaz from `root_hz`."""
    octave, idx = divmod(scale_step, 7)
    semitones = HIJAZ_STEPS[idx] + 12 * octave
    return root_hz * (2 ** (semitones / 12.0))


def adsr(n: int, attack: float, release: float) -> np.ndarray:
    a = max(1, int(attack * SR))
    r = max(1, int(release * SR))
    env = np.ones(n, dtype=np.float32)
    if n > a + r:
        env[:a] = np.linspace(0, 1, a)
        env[-r:] = np.linspace(1, 0, r)
    else:
        env = np.linspace(0, 1, n) * np.linspace(1, 0, n)
    return env


def daff_hit(duration_s: float = 0.18, low: bool = False) -> np.ndarray:
    """Synthesize a single frame-drum hit — low (dum) or high (tak)."""
    n = int(duration_s * SR)
    t = np.arange(n) / SR
    if low:
        # Dum: low thump with rapid pitch drop.
        f = 95 * np.exp(-12 * t) + 50
        sig = 0.9 * np.sin(2 * np.pi * np.cumsum(f) / SR)
        sig += 0.3 * np.random.randn(n).astype(np.float32)
    else:
        # Tak: sharp click + rim ring.
        f = 380 * np.exp(-25 * t) + 220
        sig = 0.6 * np.sin(2 * np.pi * np.cumsum(f) / SR)
        sig += 0.5 * np.random.randn(n).astype(np.float32) * np.exp(-30 * t)
    env = np.exp(-9 * t)
    return (sig * env).astype(np.float32)


def daff_pattern(duration_s: float, bpm: int = 96) -> np.ndarray:
    """A simple Khaleeji-style daff loop: D _ T _ D D T _ per bar."""
    bar_s = 60.0 / bpm * 4         # 4 beats per bar
    eighth = bar_s / 8
    pattern = [
        (0.0, True),   # D
        (eighth * 2, False),   # T
        (eighth * 4, True),    # D
        (eighth * 5, True),    # D
        (eighth * 6, False),   # T
    ]
    n = int(duration_s * SR)
    track = np.zeros(n, dtype=np.float32)
    t = 0.0
    while t < duration_s:
        for offset, is_low in pattern:
            hit_start = int((t + offset) * SR)
            hit = daff_hit(low=is_low)
            end = min(hit_start + len(hit), n)
            if hit_start >= n:
                break
            track[hit_start:end] += hit[: end - hit_start] * 0.6
        t += bar_s
    return track


def oud_phrase(duration_s: float, root_hz: float) -> np.ndarray:
    """A simple looped Hijaz arpeggio that imitates an oud bed."""
    n = int(duration_s * SR)
    track = np.zeros(n, dtype=np.float32)
    # Repeating 4-note Hijaz figure: root, 3rd, 5th, 4th.
    figure = [0, 2, 4, 3]
    note_dur = 0.4
    note_n = int(note_dur * SR)
    pos = 0
    i = 0
    while pos < n:
        step = figure[i % len(figure)]
        f = hz(root_hz, step)
        t = np.arange(note_n) / SR
        # Plucked-string-ish: bright attack, exponential decay.
        sig = np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * f * 2 * t)
        sig *= np.exp(-3 * t)
        end = min(pos + note_n, n)
        track[pos:end] += sig[: end - pos].astype(np.float32) * 0.35
        pos += note_n
        i += 1
    return track


def ney_layer(duration_s: float, root_hz: float, name_slots: list[tuple[float, float]]) -> np.ndarray:
    """A sustained breathy melodic line that *drops out* during name slots
    so the cloned voice has empty space to slot into.

    Uses a Hijaz scalar walk with slow vibrato + lots of air noise.
    """
    n = int(duration_s * SR)
    track = np.zeros(n, dtype=np.float32)
    # Walk through Hijaz steps slowly — 2 seconds per note.
    walk = [4, 3, 2, 4, 5, 4, 3, 0, 2, 3, 4]
    note_dur = 2.0
    note_n = int(note_dur * SR)
    pos = 0
    i = 0
    while pos < n:
        step = walk[i % len(walk)]
        f = hz(root_hz, step)
        t = np.arange(note_n) / SR
        vibrato = 1.0 + 0.012 * np.sin(2 * np.pi * 5.5 * t)
        sig = np.sin(2 * np.pi * f * vibrato * t)
        # Breath noise + filtered envelope to mimic a ney's airy timbre.
        breath = 0.18 * np.random.randn(note_n).astype(np.float32)
        env = adsr(note_n, attack=0.18, release=0.5)
        sig = (sig + breath) * env * 0.32
        end = min(pos + note_n, n)
        track[pos:end] += sig[: end - pos].astype(np.float32)
        pos += note_n
        i += 1

    # Carve out silence where the name segments will be spliced in,
    # leaving a small fade to avoid clicks.
    for start_s, end_s in name_slots:
        a = max(0, int((start_s - 0.05) * SR))
        b = min(n, int((end_s + 0.05) * SR))
        if b <= a:
            continue
        fade = min(int(0.04 * SR), (b - a) // 2)
        track[a + fade : b - fade] = 0.0
        if fade > 0:
            track[a : a + fade] *= np.linspace(1, 0, fade)
            track[b - fade : b] *= np.linspace(0, 1, fade)
    return track


def write_song(
    out_dir: Path,
    *,
    duration_s: float,
    bpm: int,
    root_hz: float,
    name_slots: list[tuple[float, float]],
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    np.random.seed(hash(str(out_dir)) & 0xFFFFFFFF)

    # Vocal layer = the ney that vacates the name slots.
    vocals = ney_layer(duration_s, root_hz=root_hz * 2, name_slots=name_slots)
    # Instrumental = daff + oud bed (full duration, no vacating).
    daff = daff_pattern(duration_s, bpm=bpm)
    oud = oud_phrase(duration_s, root_hz=root_hz)
    inst = (0.5 * daff + 0.8 * oud).astype(np.float32)

    # Light limiting.
    vocals = np.clip(vocals, -0.95, 0.95)
    inst = np.clip(inst, -0.95, 0.95)

    sf.write(out_dir / "vocals.wav", vocals, SR, subtype="PCM_16")
    sf.write(out_dir / "instrumental.wav", inst, SR, subtype="PCM_16")


def write_preview(song_dir: Path, public_samples: Path, slug: str) -> None:
    public_samples.mkdir(parents=True, exist_ok=True)
    mp3 = public_samples / f"preview-{slug}.mp3"
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

    # Each song's `name_slots` matches its rows in supabase/seed.sql
    # (sequence_index, start_ms, end_ms — converted to seconds).
    songs = [
        {
            "slug": "demo-classic-1", "bpm": 92, "root_hz": 146.83,  # D
            "name_slots": [(22.0, 24.5), (41.0, 43.2), (96.0, 99.0)],
        },
        {
            "slug": "demo-classic-2", "bpm": 88, "root_hz": 130.81,  # C
            "name_slots": [
                (18.0, 20.8), (35.0, 37.5), (60.0, 62.8),
                (82.0, 84.8), (110.0, 112.8), (160.0, 163.0),
            ],
        },
        {
            "slug": "demo-modern-1", "bpm": 104, "root_hz": 164.81,  # E
            "name_slots": [(14.0, 16.2), (29.0, 31.2), (88.0, 91.0)],
        },
    ]

    for s in songs:
        d = storage_root / s["slug"]
        write_song(
            d,
            duration_s=180.0,
            bpm=s["bpm"],
            root_hz=s["root_hz"],
            name_slots=s["name_slots"],
        )
        write_preview(d, public_root, s["slug"])
        print(f"  ✓ {s['slug']} → Hijaz @ {s['bpm']} BPM, {len(s['name_slots'])} name slots")

    print(f"\nstorage : {storage_root}")
    print(f"previews: {public_root}")


if __name__ == "__main__":
    main()
