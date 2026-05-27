"""Generate a placeholder watermark WAV.

The shipped `watermark.wav` is a tonal placeholder. Before launch,
replace it with a recorded voiceover saying the brand identifier in
Arabic, exported at 44.1 kHz mono PCM_16.

Run:
    python apps/api/assets/make_watermark.py
"""
from pathlib import Path

import numpy as np
import soundfile as sf

SR = 44_100
DUR = 1.2


def main() -> None:
    t = np.arange(int(SR * DUR)) / SR
    # Two soft tones, separated by a brief silence — distinctive enough
    # to be recognizable as a watermark when overlaid at low gain.
    sig = (
        0.18 * np.sin(2 * np.pi * 660 * t) * np.exp(-3 * t)
        + 0.14 * np.sin(2 * np.pi * 880 * t) * np.exp(-2 * (t - 0.6) ** 2)
    )
    sig = sig.astype(np.float32)
    out = Path(__file__).with_name("watermark.wav")
    sf.write(out, sig, SR, subtype="PCM_16")
    print(f"wrote {out} ({DUR}s @ {SR} Hz)")


if __name__ == "__main__":
    main()
