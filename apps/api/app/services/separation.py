"""Source separation via Demucs (htdemucs).

One function: `separate(src_path, out_dir)` -> (vocals_path, instrumental_path).

The worker image pre-downloads the htdemucs model at build time so the
first call doesn't pay a 30 s 80 MB download cost. Inference runs on
CPU (~6 minutes for a 3-min song on a Standard Render box).
"""
from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)


def separate(src_path: Path, out_dir: Path) -> tuple[Path, Path]:
    """Run Demucs two-stem (vocals / no_vocals) split.

    Returns (vocals_path, instrumental_path) absolute paths.
    Raises CalledProcessError if demucs CLI fails.
    """
    src_path = Path(src_path).resolve()
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    log.info("[demucs] separating %s -> %s", src_path.name, out_dir)

    # `--two-stems vocals` writes:
    #   <out_dir>/htdemucs/<stem>/vocals.wav
    #   <out_dir>/htdemucs/<stem>/no_vocals.wav
    cmd = [
        "python", "-m", "demucs",
        "--two-stems", "vocals",
        "-n", "htdemucs",
        "-o", str(out_dir),
        "--mp3-bitrate", "320",
        str(src_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)

    stem = src_path.stem
    stem_dir = out_dir / "htdemucs" / stem
    vocals = stem_dir / "vocals.wav"
    instr  = stem_dir / "no_vocals.wav"

    if not vocals.exists() or not instr.exists():
        raise RuntimeError(
            f"demucs output missing — expected {vocals} and {instr}"
        )

    # Move them up to a flat layout the rest of the pipeline expects.
    flat_vocals = out_dir / "vocals.wav"
    flat_instr  = out_dir / "instrumental.wav"
    shutil.move(str(vocals), flat_vocals)
    shutil.move(str(instr), flat_instr)
    shutil.rmtree(out_dir / "htdemucs", ignore_errors=True)

    log.info(
        "[demucs] done. vocals=%s (%.1f MB) instr=%s (%.1f MB)",
        flat_vocals.name, flat_vocals.stat().st_size / 1e6,
        flat_instr.name, flat_instr.stat().st_size / 1e6,
    )
    return flat_vocals, flat_instr
