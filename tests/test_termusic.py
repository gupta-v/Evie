import pytest

from evie.services.termusic import Termusic, TermusicError


def test_status_and_volume_steps(player):
    c = player.client
    assert c.status() == {"state": "stopped", "volume": 50, "track_index": 0, "position_s": 0, "total_s": 0}
    assert c.volume_up() == 55
    assert c.volume_down(3) == 40
    assert c.set_volume(70) == 70  # emulated absolute volume


def test_play_pause_read_state_first(player):
    c = player.client
    player.status = 1
    assert c.play() == "already playing"
    assert player.calls == []  # play while playing must not toggle
    assert c.pause() == "paused"
    assert c.pause() == "not playing"
    assert c.play() == "resumed"


def test_play_from_stopped_uses_playlist(player):
    c = player.client
    assert c.play() == "queue is empty"
    c.add("C:/music/a.mp3")
    assert c.play() == "playing"
    assert "PlaySpecific:0" in player.calls


def test_queue_add_path_and_url_then_clear(player):
    c = player.client
    c.add("C:/music/a.mp3")
    c.add("https://example.com/b")
    assert c.queue() == ["C:/music/a.mp3", "https://example.com/b"]
    c.clear()
    assert c.queue() == []


def test_server_down_gives_spoken_error():
    with pytest.raises(TermusicError, match="isn't running"):
        Termusic("127.0.0.1:1").status()
