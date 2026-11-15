"""Microphone check: lists input devices, then shows live loudness for 10 seconds. Speak and watch.

`uv run python scripts/mic_check.py`  (set EVIE_MIC to a device number or name part to test another)
Each row is about 0.15 s. Rows marked SPEECH are what Evie would treat as you talking: above its
threshold (2.5x the room's typical level, at least 250, or EVIE_THRESHOLD if you set it).
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
print(f"\nusing: {config.MIC if config.MIC is not None else 'system default'} -> device {stt.mic_device(config.MIC)}. Speak now (10 s):")
gate, quiet_run, peak = stt.Gate(quiet_blocks=10**9), 0, 0.0
for i, block in enumerate(stt._mic_blocks()):
    rms = float(np.sqrt(np.mean(block.astype("float32") ** 2)))
    gate.update(rms)
    peak = max(peak, rms) if i > 10 else peak  # ignore the click a mic makes when it opens
    if i % 5 == 0:
        mark = "SPEECH" if i > 10 and rms > gate.threshold else ""
        print(f"{'#' * min(60, int(rms / 150)):60s} {rms:6.0f}  threshold {gate.threshold:5.0f}  {mark}")
    if i >= 10 * 16000 / 480:
        break
print(f"\nloudest after the opening click: {peak:.0f} | Evie needs above about {gate.threshold:.0f}")
print("Verdict:", "your voice is clearly above the threshold" if peak > 2 * gate.threshold else "your voice barely reaches the threshold: wrong mic, too quiet, or you were silent")
