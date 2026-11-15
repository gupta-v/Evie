"""Listen and transcribe: record the mic until you stop talking, send to Groq Whisper.

Recording is a simple loudness gate (no model): it learns the room's noise for 0.3 s, waits for you to
start, and stops after about a second of quiet. Groq keys rotate if one is rate limited.

shortcut: the loudness gate misjudges noisy rooms or music playing through speakers; swap in Silero VAD
(Pipecat ships it) when that bites. One utterance at a time, push-to-talk only.
"""
import io
import time
import wave

from evie import config

RATE = 16000
_BLOCK = 480  # 30 ms
_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
_MODEL = "whisper-large-v3-turbo"
_COOLDOWN = 300  # seconds a rejected or rate-limited key is skipped
_dead: dict[str, float] = {}


class SttError(Exception):
    """Message is safe to read aloud (or print)."""


def end_of_speech(levels: list[float], thr: float, quiet_blocks: int) -> bool:
    """True once speech was heard and the last `quiet_blocks` blocks are all below `thr`."""
    spoke = any(v > thr for v in levels)
    return spoke and len(levels) >= quiet_blocks and all(v <= thr for v in levels[-quiet_blocks:])


def record(max_seconds: float = 20, wait_seconds: float = 8, quiet_seconds: float = 1.0) -> bytes:
    """Raw 16 kHz mono int16 PCM of one utterance; b'' if nobody spoke."""
    import numpy as np
    import sounddevice as sd

    chunks, levels, thr = [], [], None
    quiet_blocks = int(quiet_seconds * RATE / _BLOCK)
    with sd.InputStream(samplerate=RATE, channels=1, dtype="int16", blocksize=_BLOCK) as stream:
        for i in range(int(max_seconds * RATE / _BLOCK)):
            block, _ = stream.read(_BLOCK)
            rms = float(np.sqrt(np.mean(block.astype("float32") ** 2)))
            if i < 10:  # first 0.3 s: learn the room
                levels.append(rms)
                if i == 9:
                    thr, levels = max(250.0, 2.5 * max(levels)), []
                continue
            chunks.append(block.tobytes())
            levels.append(rms)
            if end_of_speech(levels, thr, quiet_blocks):
                break
            if not any(v > thr for v in levels) and i > wait_seconds * RATE / _BLOCK:
                return b""
    return b"".join(chunks) if any(v > thr for v in levels) else b""


def _wav(pcm: bytes) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm)
    return buf.getvalue()


def transcribe(pcm: bytes, post=None) -> str:
    """Text for `pcm` via Groq Whisper. Tries each configured key; raises SttError if none work."""
    import httpx

    if not config.GROQ_API_KEYS:
        raise SttError("No Groq key is set.")
    wav = _wav(pcm)
    for key in config.GROQ_API_KEYS:
        if _dead.get(key, 0) > time.monotonic():
            continue
        try:
            r = (post or httpx.post)(
                _URL, headers={"Authorization": f"Bearer {key}"}, timeout=15,
                files={"file": ("speech.wav", wav, "audio/wav")}, data={"model": _MODEL, "response_format": "text"},
            )
        except httpx.HTTPError as e:
            raise SttError("I couldn't reach the speech service.") from e
        if r.status_code in (401, 429):  # bad or rate-limited key: try the next
            _dead[key] = time.monotonic() + _COOLDOWN
            continue
        if r.status_code != 200:
            raise SttError(f"The speech service failed ({r.status_code}).")
        return r.text.strip()
    raise SttError("All Groq keys were rejected or rate limited.")
