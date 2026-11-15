import pytest

from evie import config
from evie.services import stt


def test_end_of_speech_needs_speech_then_quiet():
    assert not stt.end_of_speech([1, 1, 1, 1], 100, 3)          # never spoke
    assert not stt.end_of_speech([500, 500, 1, 1], 100, 3)      # spoke, not quiet long enough
    assert stt.end_of_speech([500, 500, 1, 1, 1], 100, 3)


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
