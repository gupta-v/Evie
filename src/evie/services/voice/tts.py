"""Speak replies aloud: Microsoft Edge neural voices (edge-tts, no key) played through Windows MCI.

No audio dependency: the mp3 goes to a temp file and winmm plays it, which also lets us stop it
mid-sentence (barge-in later). Text is cleaned first so emoji and markdown are not read out.

shortcut: edge-tts uses an unofficial Microsoft endpoint, so it can break or need internet; Piper is
the planned offline fallback. Playback is blocking (one reply at a time).
"""
import asyncio
import ctypes
import os
import re
import tempfile
from concurrent.futures import ThreadPoolExecutor

from evie.utils import config

_JUNK = re.compile(r"[\U0001F000-\U0001FFFF☀-➿️‍*_`#>]")


class TtsError(Exception):
    """Message is safe to read aloud (or print)."""


def clean(text: str) -> str:
    """Drop emoji and markdown marks; collapse spaces."""
    return " ".join(_JUNK.sub("", text).split())


async def _synth(text: str, path: str) -> None:
    import edge_tts

    await edge_tts.Communicate(text, config.VOICE).save(path)


def _mci(cmd: str) -> None:
    err = ctypes.windll.winmm.mciSendStringW(cmd, None, 0, None)
    if err:
        raise TtsError(f"audio playback failed (mci {err})")


def sentences(text: str) -> list[str]:
    """Split at sentence ends so the first one can start playing while the rest are still being made."""
    return [s for s in re.split(r"(?<=[.!?])\s+", text) if s]


def _to_file(text: str, synth) -> str:
    fd, path = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)
    try:
        synth(text, path)
    except Exception as e:
        _remove(path)
        raise TtsError("I couldn't reach the voice service.") from e
    return path


def _remove(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass


def speak(text: str, synth=None, play=None) -> None:
    """Say `text` and return when it finishes. Sentences are synthesized in parallel and played in
    order, so the first sound starts after ~1 sentence of work, not the whole reply.
    `synth(text, path)` and `play(path)` are injectable for tests."""
    parts = sentences(clean(text))
    if not parts:
        return
    synth = synth or (lambda t, p: asyncio.run(_synth(t, p)))
    files = []
    try:
        with ThreadPoolExecutor(max_workers=min(len(parts), 4)) as pool:
            files = [pool.submit(_to_file, s, synth) for s in parts]
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


def _play(path: str) -> None:
    _mci(f'open "{path}" type mpegvideo alias evie')
    try:
        _mci("play evie wait")
    finally:
        ctypes.windll.winmm.mciSendStringW("close evie", None, 0, None)
