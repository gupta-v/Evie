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

from evie import config

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


def speak(text: str, synth=None, play=None) -> None:
    """Say `text` and return when it finishes. `synth(text, path)` and `play(path)` are injectable for tests."""
    text = clean(text)
    if not text:
        return
    fd, path = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)
    try:
        try:
            (synth or (lambda t, p: asyncio.run(_synth(t, p))))(text, path)
        except Exception as e:
            raise TtsError("I couldn't reach the voice service.") from e
        (play or _play)(path)
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def _play(path: str) -> None:
    _mci(f'open "{path}" type mpegvideo alias evie')
    try:
        _mci("play evie wait")
    finally:
        ctypes.windll.winmm.mciSendStringW("close evie", None, 0, None)
