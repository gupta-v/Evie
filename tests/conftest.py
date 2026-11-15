from concurrent import futures

import grpc
import pytest

from evie.services.termusic import Termusic
from evie.services.termusic_pb import player_pb2 as pb
from evie.services.termusic_pb import player_pb2_grpc as rpc


class FakePlayer(rpc.MusicPlayerServicer):
    """In-memory termusic: status 0 stopped, 1 playing, 2 paused. Volume moves by 5."""

    def __init__(self):
        self.status, self.volume, self.index = 0, 50, 0
        self.tracks: list[pb.TrackId] = []
        self.calls: list[str] = []
        self.ignore_adds = False  # real termusic silently drops tracks it cannot use

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
        if self.ignore_adds:
            return pb.Empty()
        self.tracks[req.at_index:req.at_index] = list(req.tracks)
        return pb.Empty()

    def RemoveFromPlaylist(self, req, ctx):
        if req.WhichOneof("type") == "clear":
            self.tracks.clear()
        return pb.Empty()

    def QuitServer(self, req, ctx):
        self.calls.append("QuitServer")
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
