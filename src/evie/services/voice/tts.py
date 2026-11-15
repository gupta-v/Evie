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


_LANG = {"a": "en-us", "b": "en-gb", "h": "hi", "e": "es", "f": "fr-fr", "i": "it", "j": "ja"}  # first letter of a voice name


def _load_kokoro():
    """Load the model once (even if sentences start in parallel). 8 threads measured fastest on this
    28-core PC: the default and 12+ were slower, 1-2 much slower."""
    global _kokoro
    with _kokoro_lock:
        if _kokoro is None:
            model, voices = config.KOKORO_DIR / "kokoro-v1.0.int8.onnx", config.KOKORO_DIR / "voices-v1.0.bin"
            if not (model.is_file() and voices.is_file()):
                raise FileNotFoundError(f"Kokoro model files missing in {config.KOKORO_DIR}")
            import onnxruntime as rt
            from kokoro_onnx import Kokoro

            opts = rt.SessionOptions()
            opts.intra_op_num_threads, opts.inter_op_num_threads = min(8, os.cpu_count() or 4), 1
            session = rt.InferenceSession(str(model), sess_options=opts, providers=["CPUExecutionProvider"])
            _kokoro = Kokoro.from_session(session, str(voices))
    return _kokoro


def warm_up() -> None:
    """Load Kokoro in the background so the first reply does not pay the ~0.7 s load."""
    if config.TTS_ORDER and config.TTS_ORDER[0] == "kokoro":
        threading.Thread(target=lambda: _try(_load_kokoro), daemon=True).start()


def _try(fn) -> None:
    try:
        fn()
    except Exception:
        pass  # speak() reports problems; warming up is best effort


def _kokoro_synth(text: str, path: str) -> None:
    import numpy as np

    voice = config.KOKORO_VOICE
    audio, rate = _load_kokoro().create(text, voice=voice, lang=_LANG.get(voice[:1], "en-us"), speed=config.TTS_SPEED)
    # Replies are made piece by piece, so the pause Kokoro puts between sentences inside one call is lost: add it back
    audio = np.concatenate([audio, np.zeros(int(rate * (0.25 if text.rstrip()[-1:] in ".!?" else 0.1)), dtype=audio.dtype)])
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


def _make(text: str, chain) -> str:
    """Audio file for `text` from the first backend in `chain` that works."""
    error = TtsError("No voice is configured.")
    for suffix, fn in chain:
        fd, path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        try:
            fn(text, path)
            return path
        except Exception as e:
            _remove(path)
            error = TtsError("I couldn't make the voice.")
            error.__cause__ = e
    raise error


def _remove(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass


CLAUSE_MIN, CLAUSE_SKIP = 50, 20  # unfinished text this long is cut at the first comma after 20 characters


class Speaker:
    """Speaks text as it arrives: feed() pieces while the reply is still being written, finish() at the end.
    Each complete sentence is made right away (in parallel) and played in order, so the first sentence is
    audible while the model is still writing the next. `synth(text, path)` and `play(path)` are injectable."""

    def __init__(self, synth=None, play=None):
        import queue

        self._chain = [(".mp3", synth)] if synth else [_BACKENDS[n] for n in config.TTS_ORDER if n in _BACKENDS]
        self._play = play or _play
        self._pool = ThreadPoolExecutor(max_workers=3)
        self._queue: "queue.Queue" = queue.Queue()
        self._buf, self.error = "", None
        self._player = threading.Thread(target=self._run, daemon=True)
        self._player.start()

    def feed(self, text: str) -> None:
        self._buf += text
        *done, self._buf = re.split(r"(?<=[.!?])\s+", self._buf)  # the last piece may be an unfinished sentence
        for sentence in done:
            self._submit(sentence)
        while len(self._buf) >= CLAUSE_MIN and (m := re.search(r"[,;:]\s", self._buf[CLAUSE_SKIP:])):
            cut = CLAUSE_SKIP + m.end()  # a long sentence still being written: start on its first clause
            self._submit(self._buf[:cut])
            self._buf = self._buf[cut:]

    def finish(self) -> None:
        """Speak what is left, wait until everything has been said, raise the first problem."""
        self._submit(self._buf)
        self._buf = ""
        self._queue.put(None)
        self._player.join()
        self._pool.shutdown()
        if self.error:
            raise self.error

    def _submit(self, sentence: str) -> None:
        sentence = clean(sentence)
        if sentence:
            self._queue.put(self._pool.submit(_make, sentence, self._chain))

    def _run(self) -> None:
        while (future := self._queue.get()) is not None:
            try:
                path = future.result()
            except TtsError as e:
                self.error = self.error or e
                continue  # keep going: later sentences may work
            try:
                if not self.error:
                    self._play(path)
            finally:
                _remove(path)


def speak(text: str, synth=None, play=None) -> None:
    """Say `text` and return when it finishes (a reply that is already complete)."""
    speaker = Speaker(synth, play)
    speaker.feed(text)
    speaker.finish()


def _play(path: str) -> None:
    _mci(f'open "{path}" alias evie')
    try:
        _mci("play evie wait")
    finally:
        ctypes.windll.winmm.mciSendStringW("close evie", None, 0, None)
