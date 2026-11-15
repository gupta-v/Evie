"""Play each Kokoro voice saying its name: `uv run python scripts/voices_demo.py [prefix]`.

Prefix filters by voice name (af_ US female, bf_ British female, hf_ Hindi female). Default af_ and bf_.
Pick one and set EVIE_KOKORO_VOICE (or the default in src/evie/utils/config.py).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from evie.services.voice import tts
from evie.utils import config

prefixes = tuple(sys.argv[1:]) or ("af_", "bf_")
voices = sorted(v for v in tts._load_kokoro().get_voices() if v.startswith(prefixes))
for v in voices:
    config.KOKORO_VOICE = v
    print(v, flush=True)
    tts.speak(f"Hi, I'm Evie. This is the voice called {v.split('_')[1]}.")
