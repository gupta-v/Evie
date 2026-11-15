from concurrent import futures

import grpc
import pytest

from evie.services.termusic import Termusic, TermusicError
from evie.services.termusic_pb import player_pb2 as pb
from evie.services.termusic_pb import player_pb2_grpc as rpc


class FakePlayer(rpc.MusicPlayerServicer):
    """In-memory termusic: status 0 stopped, 1 playing, 2 paused. Volume moves by 5."""

    def __init__(self):
        self.status, self.volume, self.index = 0, 50, 0
        self.tracks: list[pb.TrackId] = []
        self.calls: list[str] = []

    def GetProgress(self, req, ctx):
        return pb.GetProgressResponse(status=self.status, volume=self.volume, current_track_index=self.index)

    def TogglePause(self, req, ctx):
        self.calls.append("TogglePause")
        self.status = 2 if self.status == 1 else 1
        return pb.PlayState(status=self.status)

    def VolumeUp(self, req, ctx):
        self.volume = min(100, self.volume + 5)
        return pb.VolumeReply(volume=self.volume)

    def VolumeDown(self, req, ctx):
        self.volume = max(0, self.volume - 5)
        return pb.VolumeReply(volume=self.volume)

    def SkipNext(self, req, ctx):
        self.calls.append("SkipNext")
        return pb.Empty()

    def GetPlaylist(self, req, ctx):
        return pb.PlaylistTracks(
            current_track_index=self.index,
            tracks=[pb.PlaylistAddTrack(at_index=i, id=t) for i, t in enumerate(self.tracks)],
        )

    def AddToPlaylist(self, req, ctx):
        self.tracks[req.at_index:req.at_index] = list(req.tracks)
        return pb.Empty()

    def RemoveFromPlaylist(self, req, ctx):
        if req.WhichOneof("type") == "clear":
            self.tracks.clear()
        return pb.Empty()

    def PlaySpecific(self, req, ctx):
        self.calls.append(f"PlaySpecific:{req.track_index}")
        self.index, self.status = req.track_index, 1
        return pb.Empty()


@pytest.fixture
def player():
    fake = FakePlayer()
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
    rpc.add_MusicPlayerServicer_to_server(fake, server)
    port = server.add_insecure_port("127.0.0.1:0")
    server.start()
    fake.client = Termusic(f"127.0.0.1:{port}")
    yield fake
    server.stop(0)


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
