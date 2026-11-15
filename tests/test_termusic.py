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
        Termusic("127.0.0.1:1", autostart=False).status()


def _free_port() -> int:
    import socket

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_autostart_launches_server_once_then_retries():
    from concurrent import futures

    import grpc

    from evie.services.termusic_pb import player_pb2_grpc as rpc
    from tests.conftest import FakePlayer

    port, started = _free_port(), []

    def starter():
        srv = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
        rpc.add_MusicPlayerServicer_to_server(FakePlayer(), srv)
        srv.add_insecure_port(f"127.0.0.1:{port}")
        srv.start()
        started.append(srv)

    c = Termusic(f"127.0.0.1:{port}", starter=starter, autostart=True)
    assert c.status()["volume"] == 50
    assert len(started) == 1
    c.status()
    assert len(started) == 1  # not started again
    started[0].stop(0)


def test_autostart_failure_is_spoken_and_not_repeated():
    calls = []
    c = Termusic("127.0.0.1:1", starter=lambda: calls.append(1), autostart=True)
    import evie.services.termusic as t

    t.START_WAIT = 0.5
    with pytest.raises(TermusicError, match="didn't come up"):
        c.status()
    with pytest.raises(TermusicError, match="isn't running"):
        c.status()
    assert calls == [1]


def test_stop_server_quits_gracefully_then_kills_leftovers(player):
    killed = []
    c = Termusic(player.client.addr, killer=lambda: killed.append(1) or True)
    assert c.stop_server() == "stopped"
    assert "QuitServer" in player.calls
    assert killed == [1]


def test_stop_when_not_running_reports_it_and_never_autostarts():
    started = []
    c = Termusic("127.0.0.1:1", starter=lambda: started.append(1), autostart=True, killer=lambda: False)
    assert c.stop_server() == "wasn't running"
    assert started == []
