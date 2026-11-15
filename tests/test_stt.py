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
