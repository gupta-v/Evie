"""Microphone check: lists input devices, then shows live loudness for 8 seconds. Speak and watch.

`uv run python scripts/mic_check.py`  (set EVIE_MIC to a device number or name part to test another)
Evie's recorder treats a block as speech when it is above about 3x the quietest level seen (min 250).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import sounddevice as sd

from evie.services.voice import stt
from evie.utils import config

for i, d in enumerate(sd.query_devices()):
    if d["max_input_channels"] > 0:
        print(f"{i:3d}  {d['name']}")
print(f"\nusing: {config.MIC if config.MIC is not None else 'system default'}. Speak now (8 s):")
quiet = float("inf")
with sd.InputStream(samplerate=16000, channels=1, dtype="int16", blocksize=480, device=stt.mic_device(config.MIC)) as s:
    for i in range(int(8 * 16000 / 480)):
        block, _ = s.read(480)
        rms = float(np.sqrt(np.mean(block.astype("float32") ** 2)))
        quiet = min(quiet, rms)
        if i % 5 == 0:
            print(f"{'#' * min(60, int(rms / 150)):60s} {rms:6.0f}  (speech above {max(250, 3 * quiet):.0f})")
