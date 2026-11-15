"""Listen and transcribe: record the mic until you stop talking, send to Groq Whisper.

Recording is a simple loudness gate (no model): it learns the room's noise for 0.3 s, waits for you to
start, and stops after about a second of quiet. Groq keys rotate if one is rate limited.

shortcut: the loudness gate misjudges noisy rooms or music playing through speakers; swap in Silero VAD
(Pipecat ships it) when that bites. One utterance at a time, push-to-talk only.
"""
import io
import re
import time
import wave

from evie.utils import config

RATE = 16000
_BLOCK = 480  # 30 ms
MIN_LOUD_BLOCKS = 8  # about 0.25 s of real speech: shorter is a click or a cough, not a command
_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
_MODEL = "whisper-large-v3-turbo"
_COOLDOWN = 300  # seconds a rejected or rate-limited key is skipped
_dead: dict[str, float] = {}
last_levels = {"loudest": 0.0, "needed": 0.0}  # from the latest recording, to explain 'heard nothing'


class SttError(Exception):
    """Message is safe to read aloud (or print)."""


class Gate:
    """Decides when an utterance starts and ends from block loudness.

    Speech level follows the quietest block seen so far (x3, never below 250), so a mic that opens loud
    and settles over a second (Bluetooth headsets do) does not set a threshold speech cannot reach."""

    def __init__(self, quiet_blocks: int):
        self.quiet_blocks, self.floor = quiet_blocks, float("inf")
        self.spoke, self.quiet, self.loud_blocks = False, 0, 0

    @property
    def threshold(self) -> float:
        return config.THRESHOLD or max(250.0, 3 * self.floor)

    def update(self, rms: float) -> bool:
        """Feed one block; True when the utterance is over."""
        self.floor = min(self.floor, rms)
        if rms > self.threshold:
            self.spoke, self.quiet = True, 0
            self.loud_blocks += 1
        elif self.spoke:
            self.quiet += 1
        return self.spoke and self.quiet >= self.quiet_blocks


def record(max_seconds: float = 20, wait_seconds: float | None = 8, quiet_seconds: float = 1.0) -> bytes:
    """Raw 16 kHz mono int16 PCM of one utterance (at most `max_seconds` long); b'' if nobody spoke or
    it was only a blip. Waits `wait_seconds` for speech to start (None = forever)."""
    import numpy as np
    import sounddevice as sd

    gate, chunks, peak, waited = Gate(int(quiet_seconds * RATE / _BLOCK)), [], 0.0, 0
    with sd.InputStream(samplerate=RATE, channels=1, dtype="int16", blocksize=_BLOCK, device=config.MIC) as stream:
        while len(chunks) < max_seconds * RATE / _BLOCK:
            block, _ = stream.read(_BLOCK)
            rms = float(np.sqrt(np.mean(block.astype("float32") ** 2)))
            peak = max(peak, rms)
            done = gate.update(rms)
            last_levels.update(loudest=peak, needed=gate.threshold)
            if gate.spoke:
                chunks.append(block.tobytes())
                if done:
                    break
            else:
                waited += 1
                if wait_seconds is not None and waited > wait_seconds * RATE / _BLOCK:
                    return b""
    return b"".join(chunks) if gate.loud_blocks >= MIN_LOUD_BLOCKS else b""


def _wav(pcm: bytes) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm)
    return buf.getvalue()


_PHANTOMS = {"thank you", "thanks for watching", "you", "bye", "okay"}  # what Whisper invents from near-silence


def is_phantom(text: str) -> bool:
    return re.sub(r"[^a-z ]", "", text.lower()).strip() in _PHANTOMS


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
        text = r.text.strip()
        return "" if is_phantom(text) else text
    raise SttError("All Groq keys were rejected or rate limited.")
