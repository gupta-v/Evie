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


def test_show_ui_opens_tui_once_on_first_use_and_not_a_headless_server(player):
    opened, started = [], []
    c = Termusic(
        player.client.addr, show_ui=True, starter=lambda: started.append(1),
        tui_opener=lambda: opened.append(1), tui_check=lambda: bool(opened),
    )
    c.status()
    c.status()
    assert opened == [1] and started == []


def test_show_ui_skips_opening_when_tui_already_running(player):
    opened = []
    c = Termusic(player.client.addr, show_ui=True, tui_opener=lambda: opened.append(1), tui_check=lambda: True)
    c.status()
    assert opened == []


def test_show_ui_server_down_waits_for_tui_instead_of_starting_headless():
    started, opened = [], []
    c = Termusic(
        "127.0.0.1:1", show_ui=True, autostart=True, starter=lambda: started.append(1),
        tui_opener=lambda: opened.append(1), tui_check=lambda: False,
    )
    import evie.services.termusic as t

    t.START_WAIT = 0.5
    with pytest.raises(TermusicError):
        c.status()
    assert opened == [1] and started == []


def test_stop_makes_next_command_reopen_the_tui(player):
    opened = []
    c = Termusic(player.client.addr, show_ui=True, killer=lambda: True,
                 tui_opener=lambda: opened.append(1), tui_check=lambda: False)
    c.status()
    c.stop_server()
    c.status()
    assert opened == [1, 1]


def test_play_after_fresh_open_restarts_at_first_track_not_saved_position(player):
    c = Termusic(player.client.addr, show_ui=True, tui_opener=lambda: None, tui_check=lambda: False)
    c.add("C:/m/a.mp3")
    c.add("C:/m/b.mp3")
    player.status, player.index = 1, 1  # server resumed on track 2 by itself
    assert c.play() == "playing"
    assert "PlaySpecific:0" in player.calls


def test_play_while_playing_later_leaves_it_alone(player):
    c = Termusic(player.client.addr)
    c.add("C:/m/a.mp3")
    player.status, player.index = 1, 0
    assert c.play() == "already playing"
    assert player.calls == []


def test_play_track_picks_position_and_validates(player):
    c = Termusic(player.client.addr)
    c.add("C:/m/a.mp3")
    c.add("C:/m/b.mp3")
    assert c.play_track(2) == "playing track 2"
    assert "PlaySpecific:1" in player.calls
    assert c.play_track(9) == "the queue has 2 tracks"


def test_open_tui_prefers_windows_terminal_for_cover_art(monkeypatch):
    import evie.services.termusic as t

    launched = []
    monkeypatch.setattr(t.shutil, "which", lambda n: {"termusic": "C:/s/termusic.exe", "wt": "C:/w/wt.exe"}.get(n))
    monkeypatch.setattr(t.subprocess, "Popen", lambda cmd, **kw: launched.append(cmd))
    t.open_tui()
    assert launched == [["C:/w/wt.exe", "-w", "new", "new-tab", "--title", "Evie Termusic", "--suppressApplicationTitle", "--", "C:/s/termusic.exe"]]


def test_open_tui_falls_back_to_plain_console_without_wt(monkeypatch):
    import evie.services.termusic as t

    launched = []
    monkeypatch.setattr(t.shutil, "which", lambda n: "C:/s/termusic.exe" if n == "termusic" else None)
    monkeypatch.setattr(t.subprocess, "Popen", lambda cmd, **kw: launched.append((cmd, kw)))
    t.open_tui()
    assert launched[0][0] == ["C:/s/termusic.exe"] and "creationflags" in launched[0][1]


def test_tui_launched_once_even_if_process_is_slow_to_appear(player):
    # Windows Terminal needs ~1 s before termusic.exe shows up, so tui_check keeps saying "no"
    opened = []
    c = Termusic(player.client.addr, show_ui=True, tui_opener=lambda: opened.append(1), tui_check=lambda: False)
    c.status()  # first music call launches it
    assert c.open_ui() == "already open"  # the explicit "start terminal music" call must not launch again
    c.open_ui()
    assert opened == [1]


def test_tui_relaunched_after_grace_if_user_closed_it(player, monkeypatch):
    import evie.services.termusic as t

    opened = []
    c = Termusic(player.client.addr, show_ui=True, tui_opener=lambda: opened.append(1), tui_check=lambda: False)
    c.open_ui()
    monkeypatch.setattr(t, "UI_GRACE", 0)  # grace over: the window is really gone
    assert c.open_ui() == "opened"
    assert opened == [1, 1]
