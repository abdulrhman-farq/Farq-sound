"""Audio post-processing helpers used by the Celery render chain.

Each function corresponds to one stage of the rendering pipeline:
  Stage 1 — TTS         (handled by `app.services.tts`)
  Stage 2 — pitch_match (this file: `pitch_and_time_match`)
  Stage 3 — splice      (this file: `splice_into_vocals`)
  Stage 4 — mixdown     (this file: `mixdown`)
  Stage 5 — master      (this file: `master_to_mp3`)
"""
from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf

log = logging.getLogger(__name__)


def slice_reference(
    source_path: Path,
    start_ms: int,
    end_ms: int,
    out_path: Path,
) -> Path:
    """Slice [start_ms, end_ms] from `source_path` and write to `out_path`.

    Used to extract the original-singer segment that the generated audio
    should match in pitch and duration.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    audio, sr = sf.read(source_path)
    if audio.ndim > 1:
        audio = np.mean(audio, axis=1)
    start = max(0, int(start_ms / 1000.0 * sr))
    end = min(len(audio), int(end_ms / 1000.0 * sr))
    sf.write(out_path, audio[start:end].astype(np.float32), sr)
    return out_path


# ---------------------------------------------------------------------
# Stage 2 — pitch & time match
# ---------------------------------------------------------------------
def pitch_and_time_match(
    generated_path: Path,
    reference_path: Path,
    target_duration_ms: int,
    out_path: Path,
) -> Path:
    """Time-stretch + pitch-shift `generated_path` to match the duration
    and pitch contour of `reference_path` (the original segment).
    """
    import gc

    import librosa

    out_path.parent.mkdir(parents=True, exist_ok=True)

    # float32 throughout — librosa defaults to float64 which doubles RAM.
    gen, sr_gen = librosa.load(
        generated_path, sr=None, mono=True, dtype=np.float32
    )
    ref, sr_ref = librosa.load(
        reference_path, sr=None, mono=True, dtype=np.float32
    )

    if sr_gen != sr_ref:
        gen = librosa.resample(gen, orig_sr=sr_gen, target_sr=sr_ref)
        sr_gen = sr_ref

    target_samples = int(round(target_duration_ms / 1000.0 * sr_gen))
    if len(gen) == 0:
        gen = np.zeros(target_samples, dtype=np.float32)

    # 1. Time-stretch to match target duration.
    rate = max(0.5, min(2.0, len(gen) / max(target_samples, 1)))
    stretched = librosa.effects.time_stretch(gen, rate=rate)

    # 2. Estimate dominant pitch of the original segment and match.
    try:
        f0_ref, _, _ = librosa.pyin(
            ref, fmin=80, fmax=600, sr=sr_ref
        )
        f0_gen, _, _ = librosa.pyin(
            stretched, fmin=80, fmax=600, sr=sr_gen
        )
        med_ref = np.nanmedian(f0_ref)
        med_gen = np.nanmedian(f0_gen)
        if np.isfinite(med_ref) and np.isfinite(med_gen) and med_gen > 0:
            n_steps = 12 * np.log2(med_ref / med_gen)
            n_steps = float(np.clip(n_steps, -3.0, 3.0))
            stretched = librosa.effects.pitch_shift(
                stretched, sr=sr_gen, n_steps=n_steps
            )
    except Exception as exc:  # pragma: no cover — best-effort
        log.warning("pitch detection failed, skipping shift: %s", exc)

    # 3. Hard-trim/pad to the exact target sample count.
    if len(stretched) > target_samples:
        stretched = stretched[:target_samples]
    else:
        stretched = np.pad(stretched, (0, target_samples - len(stretched)))

    sf.write(out_path, stretched.astype(np.float32), sr_gen)
    # Drop large arrays before returning so the next stage starts clean.
    del gen, ref, stretched
    gc.collect()
    return out_path


# ---------------------------------------------------------------------
# Stage 3 — splice
# ---------------------------------------------------------------------
def splice_into_vocals(
    isolated_vocals_path: Path,
    replacements: list[tuple[int, int, Path]],
    out_path: Path,
    crossfade_ms: int = 30,
) -> Path:
    """For each `(start_ms, end_ms, segment_path)` tuple, replace the
    corresponding region of the isolated vocal track with the segment
    audio, applying an equal-power crossfade on both edges.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Force float32 + always_2d=False to halve memory vs the float64 default.
    vocals, sr = sf.read(isolated_vocals_path, dtype="float32", always_2d=False)
    if vocals.ndim > 1:
        vocals = np.mean(vocals, axis=1, dtype=np.float32)

    xfade_samples = int(crossfade_ms / 1000.0 * sr)

    for start_ms, end_ms, seg_path in replacements:
        start = int(start_ms / 1000.0 * sr)
        end = int(end_ms / 1000.0 * sr)
        new_seg, sr_seg = sf.read(seg_path, dtype="float32", always_2d=False)
        if new_seg.ndim > 1:
            new_seg = np.mean(new_seg, axis=1, dtype=np.float32)
        # Trim/pad to fit the slot exactly.
        slot_len = end - start
        if len(new_seg) > slot_len:
            new_seg = new_seg[:slot_len]
        elif len(new_seg) < slot_len:
            new_seg = np.pad(new_seg, (0, slot_len - len(new_seg)))

        # Equal-power crossfade at both edges.
        fade = np.linspace(0.0, 1.0, num=max(xfade_samples, 1))
        ramp_in = np.sqrt(fade)
        ramp_out = np.sqrt(1.0 - fade)
        n = min(xfade_samples, slot_len)
        if n > 0:
            new_seg[:n] = new_seg[:n] * ramp_in[:n] + vocals[start:start + n] * ramp_out[:n]
            new_seg[-n:] = new_seg[-n:] * ramp_out[:n] + vocals[end - n:end] * ramp_in[:n]
        vocals[start:end] = new_seg

    sf.write(out_path, vocals, sr)
    return out_path


# ---------------------------------------------------------------------
# Stage 4 — mixdown (vocals + instrumental)
# ---------------------------------------------------------------------
def mixdown(
    vocals_path: Path,
    instrumental_path: Path,
    out_path: Path,
    target_lufs: float = -14.0,
) -> Path:
    """Sum vocals + instrumental, apply a soft limiter, and normalize to
    `target_lufs`. ffmpeg's `loudnorm` filter handles the LUFS pass.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(".mix.wav")
    cmd = [
        "ffmpeg", "-y",
        "-i", str(vocals_path),
        "-i", str(instrumental_path),
        "-filter_complex",
        "[0:a][1:a]amix=inputs=2:duration=longest:dropout_transition=0[a]",
        "-map", "[a]",
        "-c:a", "pcm_s16le",
        str(tmp),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # LUFS normalization pass.
    cmd2 = [
        "ffmpeg", "-y",
        "-i", str(tmp),
        "-af", f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11",
        str(out_path),
    ]
    subprocess.run(cmd2, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    tmp.unlink(missing_ok=True)
    return out_path


# ---------------------------------------------------------------------
# Stage 5 — master & deliver
# ---------------------------------------------------------------------
def master_to_mp3(
    wav_path: Path,
    out_path: Path,
    *,
    bitrate: str = "320k",
    title: str = "",
    artist: str = "",
    comment: str = "Personalized by Farq Sound",
) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-i", str(wav_path),
        "-b:a", bitrate,
        "-metadata", f"title={title}",
        "-metadata", f"artist={artist}",
        "-metadata", f"comment={comment}",
        str(out_path),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return out_path


def add_preview_watermark(
    input_mp3: Path,
    watermark_wav: Path,
    out_path: Path,
    every_seconds: int = 20,
) -> Path:
    """Overlay a soft watermark voiceover every `every_seconds`."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not watermark_wav.exists():
        # Fall back to copying — better to ship preview without WM than fail.
        shutil.copy(input_mp3, out_path)
        return out_path
    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_mp3),
        "-stream_loop", "-1", "-i", str(watermark_wav),
        "-filter_complex",
        f"[1:a]aloop=loop=-1:size=2e+09,volume=0.25,"
        f"adelay={every_seconds * 1000}|{every_seconds * 1000}[wm];"
        f"[0:a][wm]amix=inputs=2:duration=first[a]",
        "-map", "[a]",
        "-b:a", "192k",
        str(out_path),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return out_path
