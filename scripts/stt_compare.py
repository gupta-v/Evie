"""Compare speech-to-text options on YOUR voice: `uv run python scripts/stt_compare.py`

Say a sentence (Hinglish is fine); it records once, then prints what each option heard and how long it took.
Repeat as many times as you like, Ctrl+C to stop. Options: on-device Whisper (base, small), Groq's cloud
Whisper (large-v3-turbo, large-v3), and Google's free web speech API through SpeechRecognition (en-IN, hi-IN).
Cloud options send your audio to that service.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.stdout.reconfigure(encoding="utf-8")

import numpy as np

from evie.services.voice import stt
from evie.utils import config

_models: dict = {}


def whisper(name: str):
    def run(pcm: bytes) -> str:
        if name not in _models:
            from faster_whisper import WhisperModel

            _models[name] = WhisperModel(name, device="cpu", compute_type="int8", cpu_threads=8, download_root=str(config.MODELS_DIR / "whisper"))
        audio = np.frombuffer(pcm, dtype="int16").astype("float32") / 32768
        segs, info = _models[name].transcribe(audio, language=None, beam_size=1, condition_on_previous_text=False, initial_prompt=stt._prompt())
        return f"{' '.join(s.text.strip() for s in segs)}  [{info.language}]"
    return run


def groq(model: str):
    def run(pcm: bytes) -> str:
        old, stt._MODEL = stt._MODEL, model
        try:
            return stt._transcribe_groq(pcm)
        finally:
            stt._MODEL = old
    return run


def google(language: str):
    def run(pcm: bytes) -> str:
        import speech_recognition as sr

        return sr.Recognizer().recognize_google(sr.AudioData(pcm, 16000, 2), language=language)
    return run


OPTIONS = {
    "whisper base (on-device)": whisper("base"),
    "whisper small (on-device)": whisper("small"),
    "groq large-v3-turbo (cloud)": groq("whisper-large-v3-turbo"),
    "groq large-v3 (cloud)": groq("whisper-large-v3"),
    "google en-IN (cloud)": google("en-IN"),
    "google hi-IN (cloud)": google("hi-IN"),
}


def compare(pcm: bytes) -> None:
    for name, fn in OPTIONS.items():
        t = time.time()
        try:
            text = fn(pcm)
        except Exception as e:
            text = f"(failed: {type(e).__name__}: {str(e)[:60]})"
        print(f"  {name:30s} {time.time() - t:5.2f}s  {text}", flush=True)


if __name__ == "__main__":
    print("Say a sentence after each [listening]. Ctrl+C to stop.")
    while True:
        print("\n[listening...]", flush=True)
        try:
            pcm = stt.record(wait_seconds=None)
        except KeyboardInterrupt:
            break
        if pcm:
            print(f"[recorded {len(pcm) / 32000:.1f}s]", flush=True)
            compare(pcm)
