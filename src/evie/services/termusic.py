"""gRPC client for termusic-server (default [::1]:5101). Plain functions, no LLM knowledge.

Termusic facts this relies on (lib/proto/player.proto, server.rs):
- VolumeUp/VolumeDown move volume by 5; there is no absolute set.
- TogglePause flips state, so play/pause read the status first.
- The queue takes a path or URL, not a song name.
"""
import grpc

from evie import config
from evie.services.termusic_pb import player_pb2 as pb
from evie.services.termusic_pb import player_pb2_grpc as rpc

STATUS = {0: "stopped", 1: "playing", 2: "paused"}
VOLUME_STEP = 5
RPC_TIMEOUT = 3.0


class TermusicError(Exception):
    """Server unreachable or call failed. Message is safe to read aloud."""


class Termusic:
    def __init__(self, addr: str | None = None):
        self.addr = addr or config.TERMUSIC_ADDR
        self._stub: rpc.MusicPlayerStub | None = None

    def _call(self, method: str, request=None):
        if self._stub is None:
            self._stub = rpc.MusicPlayerStub(grpc.insecure_channel(self.addr))
        try:
            return getattr(self._stub, method)(request or pb.Empty(), timeout=RPC_TIMEOUT)
        except grpc.RpcError as e:
            if e.code() in (grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED):
                raise TermusicError("The music player isn't running. Start termusic-server.") from e
            raise TermusicError(f"Music player error: {e.details()}") from e

    # --- state ---
    def status(self) -> dict:
        p = self._call("GetProgress")
        return {
            "state": STATUS.get(p.status, "unknown"),
            "volume": p.volume,
            "track_index": p.current_track_index,
            "position_s": p.progress.position.secs,
            "total_s": p.progress.total_duration.secs,
        }

    def queue(self) -> list[str]:
        """Track sources (path or url) in queue order. Titles are not in the protocol."""
        out = []
        for t in self._call("GetPlaylist").tracks:
            kind = t.id.WhichOneof("source")
            out.append(getattr(t.id, kind) if kind else "")
        return out

    # --- transport ---
    def play(self) -> str:
        st = self.status()
        if st["state"] == "playing":
            return "already playing"
        if st["state"] == "paused":
            self._call("TogglePause")
            return "resumed"
        pl = self._call("GetPlaylist")
        if not pl.tracks:
            return "queue is empty"
        i = min(st["track_index"], len(pl.tracks) - 1)
        self._call("PlaySpecific", pb.PlaylistPlaySpecific(track_index=i, id=pl.tracks[i].id))
        return "playing"

    def pause(self) -> str:
        if self.status()["state"] != "playing":
            return "not playing"
        self._call("TogglePause")
        return "paused"

    def next(self) -> None:
        self._call("SkipNext")

    def previous(self) -> None:
        self._call("SkipPrevious")

    # --- volume ---
    def volume_up(self, times: int = 1) -> int:
        return self._steps("VolumeUp", times)

    def volume_down(self, times: int = 1) -> int:
        return self._steps("VolumeDown", times)

    def set_volume(self, target: int) -> int:
        """Absolute volume emulated with relative steps (rounded to the step of 5)."""
        cur = self.status()["volume"]
        diff = round((max(0, min(100, target)) - cur) / VOLUME_STEP)
        if diff > 0:
            return self._steps("VolumeUp", diff)
        if diff < 0:
            return self._steps("VolumeDown", -diff)
        return cur

    def _steps(self, method: str, times: int) -> int:
        vol = self.status()["volume"]
        for _ in range(max(1, min(times, 20))):
            vol = self._call(method).volume
        return vol

    # --- queue ---
    def add(self, source: str) -> None:
        """Append a file path or URL to the end of the queue."""
        n = len(self._call("GetPlaylist").tracks)
        kind = "url" if source.startswith(("http://", "https://")) else "path"
        self._call("AddToPlaylist", pb.PlaylistTracksToAdd(at_index=n, tracks=[pb.TrackId(**{kind: source})]))

    def clear(self) -> None:
        self._call("RemoveFromPlaylist", pb.PlaylistTracksToRemove(clear=pb.PlaylistTracksToRemoveClear()))

    def shuffle(self) -> None:
        self._call("ShufflePlaylist")
