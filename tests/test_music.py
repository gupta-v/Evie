import pytest

import evie.tools  # noqa: F401
from evie.core import registry
from evie.services.termusic import Termusic
from evie.tools import music


@pytest.fixture(autouse=True)
def wired(player):
    music.set_client(player.client)
    yield
    music.set_client(None)


def test_all_music_tools_registered_with_metadata():
    names = {s["name"] for s in registry.specs()}
    assert {"music_play", "music_pause", "music_next", "music_volume_up", "music_add"} <= names
    assert registry.meta("music_next").fast is True
    assert registry.meta("music_status").fast is False


def test_volume_times_is_optional_in_schema():
    spec = next(s for s in registry.specs() if s["name"] == "music_volume_up")
    assert spec["input_schema"]["required"] == []


def test_volume_up_default_and_times(player):
    assert registry.call("music_volume_up", {}) == "volume 55"
    assert registry.call("music_volume_up", {"times": 3}) == "volume 70"


def test_set_volume_and_status(player):
    assert registry.call("music_set_volume", {"level": 30}) == "volume 30"
    assert registry.call("music_status", {}).startswith("stopped, volume 30")


def test_add_then_play_then_queue(player):
    assert "added" in registry.call("music_add", {"source": "C:/m/a.mp3"})
    assert registry.call("music_play", {}) == "playing"
    assert registry.call("music_queue", {}) == "1. C:/m/a.mp3"


def test_next_calls_server(player):
    registry.call("music_next", {})
    assert "SkipNext" in player.calls


def test_server_down_returns_sentence_not_error_prefix():
    music.set_client(Termusic("127.0.0.1:1"))
    out = registry.call("music_pause", {})
    assert "isn't running" in out and not out.startswith("error")
