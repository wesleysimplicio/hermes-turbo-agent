#!/usr/bin/env python3
"""Generate a simple 90-second WAV soundtrack for the Remotion video."""

from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "public" / "sound" / "hermes-100x-fast-soundtrack.wav"
SAMPLE_RATE = 48_000
DURATION = 90.0


def envelope(t: float) -> float:
    attack = min(1.0, t / 3.0)
    release = min(1.0, max(0.0, (DURATION - t) / 5.0))
    return attack * release


def tone(t: float, freq: float, gain: float) -> float:
    return math.sin(2.0 * math.pi * freq * t) * gain


def sample(t: float) -> float:
    section = int(t // 18)
    bass = [55, 62, 73, 82, 98][min(section, 4)]
    lead = [220, 247, 294, 330, 392][min(section, 4)]
    beat = 1.0 if (t * 2.0) % 1.0 < 0.065 else 0.0
    tick = 1.0 if (t * 8.0) % 1.0 < 0.018 else 0.0
    sweep = math.sin(2 * math.pi * (90 + t * 2.2) * t) * 0.025
    value = (
        tone(t, bass, 0.17)
        + tone(t, bass * 2, 0.07)
        + tone(t, lead, 0.055)
        + tone(t, lead * 1.5, 0.025)
        + beat * math.sin(2 * math.pi * 72 * t) * 0.22
        + tick * math.sin(2 * math.pi * 1600 * t) * 0.045
        + sweep
    )
    return max(-0.92, min(0.92, value * envelope(t)))


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    total = int(SAMPLE_RATE * DURATION)
    with wave.open(str(OUT), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        for idx in range(total):
            t = idx / SAMPLE_RATE
            left = sample(t)
            right = sample(t + 0.009) * 0.96
            wav.writeframesraw(struct.pack("<hh", int(left * 32767), int(right * 32767)))


if __name__ == "__main__":
    main()
