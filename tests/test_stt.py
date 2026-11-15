import pytest

from evie.utils import config
from evie.services.voice import stt


def feed(gate, levels):
    return [gate.update(v) for v in levels]


def test_gate_waits_for_speech_then_quiet():
    g = stt.Gate(quiet_blocks=3)
    assert not any(feed(g, [40, 40, 40, 40]))                 # never spoke
    assert not any(feed(g, [5000, 5000, 40, 40]))             # spoke, not quiet long enough
    assert g.update(40)                                       # third quiet block ends it


def test_gate_follows_a_mic_that_settles_from_loud():
    g = stt.Gate(quiet_blocks=3)
    feed(g, [800, 700, 500, 300, 80, 50])                     # headset warm-up
    assert g.threshold == 250                                 # floor, not 3 x 800
    g.update(6000)
    assert g.spoke


class R:
    def __init__(self, code, text=""):
        self.status_code, self.text = code, text


@pytest.fixture(autouse=True)
def fresh_keys(monkeypatch):
    monkeypatch.setattr(stt, "_dead", {})
    monkeypatch.setattr(config, "STT_ORDER", ["groq"])  # tests of the cloud path; local is tested below


def test_rotates_to_next_key_when_rate_limited(monkeypatch):
    monkeypatch.setattr(config, "GROQ_API_KEYS", ["k1", "k2"])
    used = []

    def post(url, headers, **k):
        used.append(headers["Authorization"])
        return R(429) if len(used) == 1 else R(200, " hello there \n")

    assert stt.transcribe(b"\0\0" * 10, post=post) == "hello there"
    assert used == ["Bearer k1", "Bearer k2"]


def test_no_keys_or_all_rejected_is_an_error(monkeypatch):
    monkeypatch.setattr(config, "GROQ_API_KEYS", [])
    with pytest.raises(stt.SttError):
        stt.transcribe(b"\0\0")
    monkeypatch.setattr(config, "GROQ_API_KEYS", ["k"])
    with pytest.raises(stt.SttError):
        stt.transcribe(b"\0\0", post=lambda *a, **k: R(401))


def test_a_limited_key_is_skipped_on_the_next_call(monkeypatch):
    monkeypatch.setattr(config, "GROQ_API_KEYS", ["k1", "k2"])
    used = []

    def post(url, headers, **k):
        used.append(headers["Authorization"])
        return R(429) if headers["Authorization"] == "Bearer k1" else R(200, "ok")

    stt.transcribe(b"" + bytes(2), post=post)
    used.clear()
    stt.transcribe(b"" + bytes(2), post=post)
    assert used == ["Bearer k2"]


def test_phantom_phrases_from_near_silence_are_dropped():
    assert stt.is_phantom("Thank you.") and stt.is_phantom(" you ") and stt.is_phantom("Thank you for watching!")
    assert not stt.is_phantom("thank you for the music")


def test_fixed_threshold_overrides_the_learned_one(monkeypatch):
    monkeypatch.setattr(config, "THRESHOLD", 900.0)
    g = stt.Gate(quiet_blocks=2)
    g.update(5)
    assert g.threshold == 900.0
    g.update(800)
    assert not g.spoke          # below the fixed level
    g.update(1000)
    assert g.spoke and g.loud_blocks == 1


def _blocks(level, n):
    import numpy as np

    return [np.full(480, level, dtype="int16") for _ in range(n)]


def test_record_returns_the_utterance_and_stops_after_quiet():
    audio = _blocks(40, 20) + _blocks(3000, 20) + _blocks(40, 40)   # room, speech, quiet
    pcm = stt.record(blocks=iter(audio))
    assert len(pcm) == (stt.PREROLL_BLOCKS + 20 + 23) * 480 * 2  # lead-in, speech, and the 0.7 s of quiet that ended it


def test_record_ignores_a_blip():
    assert stt.record(blocks=iter(_blocks(40, 20) + _blocks(3000, 3) + _blocks(40, 40)), wait_seconds=2) == b""


def test_a_click_then_real_speech_returns_the_speech():
    audio = _blocks(40, 15) + _blocks(9000, 1) + _blocks(40, 40) + _blocks(3000, 20) + _blocks(40, 40)
    assert len(stt.record(blocks=iter(audio))) == (stt.PREROLL_BLOCKS + 20 + 23) * 480 * 2


def test_a_mic_that_gives_only_silence_is_an_error_not_a_freeze():
    with pytest.raises(stt.SttError):
        stt.record(wait_seconds=None, blocks=iter(_blocks(0, 400)))


def test_steady_noise_is_dropped_but_varying_speech_is_kept():
    import numpy as np

    steady = _blocks(40, 20) + _blocks(3000, 400)                      # a hum for 12 s
    assert stt.record(blocks=iter(steady)) == b""
    rng = np.random.default_rng(1)
    talking = [np.full(480, int(v), dtype="int16") for v in rng.integers(800, 6000, 400)]
    assert len(stt.record(blocks=iter(_blocks(40, 20) + talking + _blocks(40, 40)))) > 0   # 12 s of varying level


def test_mic_device_resolves_a_name_to_the_first_input_with_it():
    devs = [{"name": "Speakers", "max_input_channels": 0}, {"name": "Headset", "max_input_channels": 1},
            {"name": "Microphone (Realtek(R) Audio)", "max_input_channels": 1}, {"name": "Microphone (Realtek HD)", "max_input_channels": 1}]
    assert stt.mic_device("realtek", devs) == 2
    assert stt.mic_device(None, devs) is None and stt.mic_device(7, devs) == 7
    with pytest.raises(stt.SttError):
        stt.mic_device("nothing", devs)


def test_the_spoken_language_is_sent_to_whisper(monkeypatch):
    monkeypatch.setattr(config, "GROQ_API_KEYS", ["k"])
    monkeypatch.setattr(config, "STT_LANGUAGE", "hi")
    seen = {}

    def post(url, headers, data, **k):
        seen.update(data)
        return R(200, "namaste")

    assert stt.transcribe(bytes(2), post=post) == "namaste" and seen["language"] == "hi"


def test_on_device_speech_is_tried_first_and_the_cloud_is_the_backup(monkeypatch):
    monkeypatch.setattr(config, "STT_ORDER", ["local", "groq"])
    monkeypatch.setattr(config, "GROQ_API_KEYS", ["k"])
    monkeypatch.setattr(stt, "_transcribe_local", lambda pcm: "from this pc")
    assert stt.transcribe(b"", post=lambda *a, **k: pytest.fail("cloud must not be called")) == "from this pc"

    def broken(pcm):
        raise RuntimeError("model missing")

    monkeypatch.setattr(stt, "_transcribe_local", broken)
    assert stt.transcribe(b"", post=lambda *a, **k: R(200, "from the cloud")) == "from the cloud"
