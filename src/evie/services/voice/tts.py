"""Speak replies aloud. Backends, tried in the order of EVIE_TTS (default "kokoro,edge"):
kokoro: local Kokoro-82M (int8 ONNX), no network, ~0.5 s per sentence on this PC.
edge: Microsoft Edge neural voices (edge-tts, no key), needs internet, ~0.7 s to first sound.
If one fails the next is tried. Audio goes to a temp file and Windows MCI plays it (no audio dependency).
Replies are split into sentences that are made in parallel and played in order, so sound starts early.
Text is cleaned first so emoji and markdown are not read out.

shortcut: edge-tts uses an unofficial Microsoft endpoint; Kokoro has no Indian-English voice (US/UK only,
plus Hindi voices); Piper is not added. Playback is blocking (one reply at a time).
"""
import asyncio
import ctypes
import os
import re
import tempfile
import threading
import wave
from concurrent.futures import ThreadPoolExecutor

from evie.utils import config

_JUNK = re.compile(r"[\U0001F000-\U0001FFFF☀-➿️‍*_`#>]")


class TtsError(Exception):
    """Message is safe to read aloud (or print)."""


def clean(text: str) -> str:
    """Drop emoji and markdown marks; collapse spaces."""
    return " ".join(_JUNK.sub("", text).split())


async def _edge_async(text: str, path: str) -> None:
    import edge_tts

    await edge_tts.Communicate(text, config.VOICE).save(path)


def _edge(text: str, path: str) -> None:
    asyncio.run(_edge_async(text, path))


_kokoro = None
_kokoro_lock = threading.Lock()


def _kokoro_synth(text: str, path: str) -> None:
    global _kokoro
    import numpy as np

    with _kokoro_lock:  # load once, even if sentences start in parallel
        if _kokoro is None:
            model, voices = config.KOKORO_DIR / "kokoro-v1.0.int8.onnx", config.KOKORO_DIR / "voices-v1.0.bin"
            if not (model.is_file() and voices.is_file()):
                raise FileNotFoundError(f"Kokoro model files missing in {config.KOKORO_DIR}")
            from kokoro_onnx import Kokoro

            _kokoro = Kokoro(str(model), str(voices))
    audio, rate = _kokoro.create(text, voice=config.KOKORO_VOICE, lang="en-us")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes((np.clip(audio, -1, 1) * 32767).astype("int16").tobytes())


_BACKENDS = {"kokoro": (".wav", _kokoro_synth), "edge": (".mp3", _edge)}


def _mci(cmd: str) -> None:
    err = ctypes.windll.winmm.mciSendStringW(cmd, None, 0, None)
    if err:
        raise TtsError(f"audio playback failed (mci {err})")


def sentences(text: str) -> list[str]:
    """Split at sentence ends so the first one can start playing while the rest are still being made."""
    return [s for s in re.split(r"(?<=[.!?])\s+", text) if s]


def _to_file(text: str, synth, suffix: str) -> str:
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    try:
        synth(text, path)
    except Exception as e:
        _remove(path)
        raise TtsError("I couldn't make the voice.") from e
    return path


def _remove(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass


def _speak_with(parts: list[str], synth, suffix: str, play) -> None:
    files = []
    try:
        with ThreadPoolExecutor(max_workers=min(len(parts), 4)) as pool:
            files = [pool.submit(_to_file, s, synth, suffix) for s in parts]
            for f in files:
                path = f.result()
                try:
                    (play or _play)(path)
                finally:
                    _remove(path)
    finally:  # after the pool has finished everything: remove files made but never played
        for f in files:
            if f.done() and not f.cancelled() and not f.exception():
                _remove(f.result())


def speak(text: str, synth=None, play=None) -> None:
    """Say `text` and return when it finishes, using the first backend that works.
    `synth(text, path)` (replaces the backends) and `play(path)` are injectable for tests."""
    parts = sentences(clean(text))
    if not parts:
        return
    chain = [(".mp3", synth)] if synth else [_BACKENDS[n] for n in config.TTS_ORDER if n in _BACKENDS]
    for i, (suffix, fn) in enumerate(chain):
        try:
            return _speak_with(parts, fn, suffix, play)
        except TtsError:
            if i == len(chain) - 1:
                raise
    raise TtsError("No voice is configured.")


def _play(path: str) -> None:
    _mci(f'open "{path}" alias evie')
    try:
        _mci("play evie wait")
    finally:
        ctypes.windll.winmm.mciSendStringW("close evie", None, 0, None)
