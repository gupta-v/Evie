"""Listen and transcribe: record the mic until you stop talking, send to Groq Whisper.

Recording is a simple loudness gate (no model): it learns the room's noise for 0.3 s, waits for you to
start, and stops after about a second of quiet. Groq keys rotate if one is rate limited.

shortcut: the loudness gate misjudges noisy rooms or music playing through speakers; swap in Silero VAD
(Pipecat ships it) when that bites. One utterance at a time, push-to-talk only.
"""
import io
import re
import threading
import time
import wave

from evie.utils import config

RATE = 16000
_BLOCK = 480  # 30 ms
STEADY_SECONDS, STEADY_VARIATION = 5, 0.2  # speech rises and falls; a hum, fan or music bed stays flat
PREROLL_BLOCKS = 12  # about 0.4 s kept from before the level crossed the threshold: soft starts ("hey") would be cut
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

    Loudness is a running average of 5 blocks (0.15 s), so one click or noise spike does not count. The
    speech level is 2.5x the room's typical level (median of the last ~3 s of non-speech), never below 250:
    a noisy PC mic (level 100-400 all the time) stays under it, and a mic that opens loud and settles
    over a second (Bluetooth headsets) adjusts within a few seconds."""

    def __init__(self, quiet_blocks: int):
        from collections import deque

        self.quiet_blocks = quiet_blocks
        self._recent, self._noise = deque(maxlen=5), deque(maxlen=100)
        self.spoke, self.quiet, self.loud_blocks = False, 0, 0

    @property
    def threshold(self) -> float:
        if config.THRESHOLD:
            return config.THRESHOLD
        noise = sorted(self._noise)
        return max(250.0, 2.5 * noise[len(noise) // 2]) if noise else 250.0

    def update(self, rms: float) -> bool:
        """Feed one block; True when the utterance is over."""
        self._recent.append(rms)
        level = sum(self._recent) / len(self._recent)
        loud = len(self._noise) >= 10 and level > self.threshold  # the first 0.3 s only teaches the room
        if not loud:
            self._noise.append(level)
        if loud:
            self.spoke, self.quiet = True, 0
            self.loud_blocks += 1
        elif self.spoke:
            self.quiet += 1
        return self.spoke and self.quiet >= self.quiet_blocks


def mic_device(setting, devices=None):
    """Input device index for EVIE_MIC: a number as is, a name part matched to the first input with it
    (the same mic is listed once per audio API, so a bare name is ambiguous), None for the default."""
    if setting is None or isinstance(setting, int):
        return setting
    import sounddevice as sd

    for i, d in enumerate(devices if devices is not None else sd.query_devices()):
        if d["max_input_channels"] > 0 and setting.lower() in d["name"].lower():
            return i
    raise SttError(f"No microphone matching '{setting}'.")


def _mic_blocks():
    """Mic blocks as int16 arrays. A callback feeds a queue, so waiting can be interrupted with Ctrl+C
    (a blocking read inside the audio driver cannot) and a stalled device is noticed after 3 s."""
    import queue

    import sounddevice as sd

    q: queue.Queue = queue.Queue()
    with sd.InputStream(samplerate=RATE, channels=1, dtype="int16", blocksize=_BLOCK, device=mic_device(config.MIC),
                        callback=lambda data, frames, time_info, status: q.put(data.copy())):
        while True:
            try:
                yield q.get(timeout=3)
            except queue.Empty:
                raise SttError("The microphone stopped responding.") from None


def record(max_seconds: float = 20, wait_seconds: float | None = 8, quiet_seconds: float = 0.7, blocks=None) -> bytes:
    """Raw 16 kHz mono int16 PCM of one utterance (at most `max_seconds` long); b'' if nobody spoke or
    it was only a blip. Waits `wait_seconds` for speech to start (None = forever).
    Raises SttError if the mic stalls or gives only silence for 5 s (a muted or mis-switched Bluetooth
    headset does this): the caller reopens it. `blocks` is an iterable of int16 arrays (tests)."""
    from collections import deque

    import numpy as np

    recent = deque(maxlen=int(STEADY_SECONDS * RATE / _BLOCK))  # loudness while 'speaking'
    preroll = deque(maxlen=PREROLL_BLOCKS)
    gate, chunks, peak, waited, dead = Gate(int(quiet_seconds * RATE / _BLOCK)), [], 0.0, 0, 0
    for block in (blocks if blocks is not None else _mic_blocks()):
        rms = float(np.sqrt(np.mean(block.astype("float32") ** 2)))
        peak = max(peak, rms)
        dead = dead + 1 if rms <= 1 else 0
        if dead > 5 * RATE / _BLOCK:
            raise SttError("The microphone is giving only silence. Is it muted? (A Bluetooth headset may need EVIE_MIC set to another mic.)")
        was_speaking = gate.spoke
        done = gate.update(rms)
        last_levels.update(loudest=peak, needed=gate.threshold)
        if gate.spoke:
            if not was_speaking:
                chunks.extend(preroll)
            chunks.append(block.tobytes())
            recent.append(rms)
            if len(recent) == recent.maxlen and np.std(recent) < STEADY_VARIATION * np.mean(recent):
                return b""  # loud but not changing for 5 s: noise, not a person talking
            if done and gate.loud_blocks < MIN_LOUD_BLOCKS:  # a click (mics make one when they open), not speech: keep waiting
                gate.spoke, gate.quiet, gate.loud_blocks, chunks = False, 0, 0, []
                recent.clear()
            elif done or len(chunks) >= max_seconds * RATE / _BLOCK:
                break
        else:
            preroll.append(block.tobytes())
            waited += 1
            if wait_seconds is not None and waited > wait_seconds * RATE / _BLOCK:
                return b""
    return b"".join(chunks)


def _wav(pcm: bytes) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm)
    return buf.getvalue()


_PHANTOMS = {"thank you", "thanks for watching", "thank you for watching", "thanks", "you", "bye", "okay"}  # what Whisper invents from near-silence


def is_phantom(text: str) -> bool:
    return re.sub(r"[^a-z ]", "", text.lower()).strip() in _PHANTOMS


_local = None
_local_lock = threading.Lock()


def _load_local():
    """faster-whisper (CTranslate2, int8, CPU), loaded once; files live in models/whisper/."""
    global _local
    with _local_lock:
        if _local is None:
            from faster_whisper import WhisperModel

            _local = WhisperModel(config.STT_MODEL, device="cpu", compute_type="int8", cpu_threads=8,
                                  download_root=str(config.MODELS_DIR / "whisper"))
    return _local


def warm_up() -> None:
    """Load the on-device model in the background so the first sentence does not wait for it."""
    if config.STT_ORDER and config.STT_ORDER[0] == "local":
        threading.Thread(target=lambda: _quiet(_load_local), daemon=True).start()


def _quiet(fn) -> None:
    try:
        fn()
    except Exception:
        pass  # transcribe() reports problems; warming up is best effort


def _transcribe_local(pcm: bytes) -> str:
    import numpy as np

    audio = np.frombuffer(pcm, dtype="int16").astype("float32") / 32768
    segments, _ = _load_local().transcribe(audio, language=config.STT_LANGUAGE, beam_size=1,
                                           condition_on_previous_text=False, initial_prompt="Hey Evie.")
    return " ".join(s.text.strip() for s in segments).strip()


def transcribe(pcm: bytes, post=None) -> str:
    """Text for `pcm`, from the first backend in EVIE_STT that works ("local" = on this PC, "groq" = cloud).
    Phantom phrases come back as ''. Raises SttError if every backend fails."""
    error = SttError("No speech backend is configured.")
    for name in config.STT_ORDER:
        try:
            text = _transcribe_local(pcm) if name == "local" else _transcribe_groq(pcm, post)
        except SttError as e:
            error = e
            continue
        except Exception as e:
            if name != "local":
                raise
            error = SttError("The on-device speech model failed.")
            error.__cause__ = e
            continue
        return "" if is_phantom(text) else text
    raise error


def _transcribe_groq(pcm: bytes, post=None) -> str:
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
                files={"file": ("speech.wav", wav, "audio/wav")}, data={"model": _MODEL, "response_format": "text", "language": config.STT_LANGUAGE, "prompt": "Hey Evie."},
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
