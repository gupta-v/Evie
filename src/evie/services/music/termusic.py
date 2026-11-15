"""gRPC client for termusic-server (default [::1]:5101). Plain functions, no LLM knowledge.

Termusic facts this relies on (lib/proto/player.proto, server.rs):
- VolumeUp/VolumeDown move volume by 5; there is no absolute set.
- TogglePause flips state, so play/pause read the status first.
- The queue takes a path or URL, not a song name.
"""
import csv
import shutil
import subprocess
import time
from typing import Callable

import grpc

from evie import config
from evie.services.music.termusic_pb import player_pb2 as pb
from evie.services.music.termusic_pb import player_pb2_grpc as rpc

STATUS = {0: "stopped", 1: "playing", 2: "paused"}
VOLUME_STEP = 5
RPC_TIMEOUT = 3.0
START_WAIT = 10.0
UI_GRACE = 15.0  # seconds to trust our own TUI launch before checking the process list again


class TermusicError(Exception):
    """Server unreachable or call failed. Message is safe to read aloud."""


def start_server() -> None:
    """Launch termusic-server detached, with no console window. Argv list, never a shell string."""
    exe = shutil.which("termusic-server")
    if not exe:
        raise TermusicError("I can't find termusic-server on this PC.")
    # Not DETACHED_PROCESS: the scoop shim spawns the real exe, and a console-less parent makes
    # Windows open a visible console for the child. A hidden console is inherited instead.
    flags = sum(getattr(subprocess, f, 0) for f in ("CREATE_NEW_PROCESS_GROUP", "CREATE_NO_WINDOW"))
    subprocess.Popen(
        [exe], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags
    )


def tui_pids() -> list[int]:
    """Process ids of running termusic TUIs (the shim and the real exe both show up), oldest first."""
    exe = shutil.which("tasklist")
    if not exe:
        return []
    out = subprocess.run([exe, "/FI", "IMAGENAME eq termusic.exe", "/FO", "CSV", "/NH"], capture_output=True, text=True, timeout=10)
    rows = csv.reader(out.stdout.splitlines())
    return sorted(int(r[1]) for r in rows if len(r) > 1 and r[0].lower() == "termusic.exe")


def tui_running() -> bool:
    return bool(tui_pids())


def open_tui() -> None:
    """Open the termusic TUI in its own window. The TUI starts termusic-server itself.

    Windows Terminal when available: cover art uses sixel/kitty/iterm2 graphics, which a plain
    console window cannot draw (it falls back to blurry blocks)."""
    exe = shutil.which("termusic")
    if not exe:
        raise TermusicError("I can't find termusic on this PC.")
    wt = shutil.which("wt")
    if wt:
        subprocess.Popen([wt, "-w", "new", exe])
    else:
        subprocess.Popen([exe], creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0))


def kill_processes() -> bool:
    """Force-kill every termusic* process (same effect as the PowerShell `termusic-kill-server`).
    True if something was killed. Argv list, no shell."""
    exe = shutil.which("taskkill")
    if not exe:
        raise TermusicError("I can't stop the music player: taskkill is missing.")
    r = subprocess.run([exe, "/F", "/IM", "termusic*"], capture_output=True, timeout=10)
    return r.returncode == 0


class Termusic:
    def __init__(
        self,
        addr: str | None = None,
        starter: Callable[[], None] | None = None,
        autostart: bool | None = None,
        killer: Callable[[], bool] | None = None,
        tui_opener: Callable[[], None] | None = None,
        tui_check: Callable[[], bool] | None = None,
        show_ui: bool = False,
    ):
        self.addr = addr or config.TERMUSIC_ADDR
        self.autostart = config.TERMUSIC_AUTOSTART if autostart is None else autostart
        self.starter = starter or start_server
        self.killer = killer or kill_processes
        self.tui_opener = tui_opener or open_tui
        self.tui_check = tui_check or tui_running
        self.show_ui = show_ui  # False by default so tests never open a real window
        self._ui_checked = False
        self._ui_opened_at = float("-inf")  # monotonic time of our last TUI launch
        self._channel: grpc.Channel | None = None
        self._stub: rpc.MusicPlayerStub | None = None
        self._start_tried = False
        self._fresh = False  # Evie just brought the player up: next play starts at track 1

    def _connect(self) -> rpc.MusicPlayerStub:
        if self._stub is None:
            self._channel = grpc.insecure_channel(self.addr)
            self._stub = rpc.MusicPlayerStub(self._channel)
        return self._stub

    def _down(self, e: grpc.RpcError) -> bool:
        return e.code() in (grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED)

    def _open_if_missing(self) -> bool:
        """The only place the TUI is launched. True if a window was just opened.

        A freshly launched window takes ~1 s to appear in the process list, so for UI_GRACE seconds
        after a launch we trust our own launch instead of asking again (asking again opened duplicates).
        """
        if time.monotonic() - self._ui_opened_at < UI_GRACE or self.tui_check():
            return False
        self.tui_opener()
        self._ui_opened_at = time.monotonic()
        self._fresh = True
        return True

    def _ensure_ui(self) -> None:
        """Once per session: if the TUI window isn't open, open it. The TUI starts the server."""
        if not self.show_ui or self._ui_checked:
            return
        self._ui_checked = True
        self._open_if_missing()

    def _ensure_server(self) -> None:
        """Get the server up once (TUI-owned if show_ui, else headless), wait for the channel."""
        if not self.autostart or self._start_tried:
            raise TermusicError("The music player isn't running. Start termusic-server.")
        self._start_tried = True
        if not self.show_ui:
            self.starter()
        self._fresh = True
        self._connect()
        try:
            grpc.channel_ready_future(self._channel).result(timeout=START_WAIT)
        except grpc.FutureTimeoutError as e:
            raise TermusicError("I tried to start the music player but it didn't come up.") from e

    def _call(self, method: str, request=None):
        request = request or pb.Empty()
        self._ensure_ui()
        try:
            return getattr(self._connect(), method)(request, timeout=RPC_TIMEOUT)
        except grpc.RpcError as e:
            if not self._down(e):
                raise TermusicError(f"Music player error: {e.details()}") from e
        self._ensure_server()
        try:
            return getattr(self._connect(), method)(request, timeout=RPC_TIMEOUT)
        except grpc.RpcError as e:
            raise TermusicError(
                "The music player isn't running. Start termusic-server." if self._down(e) else f"Music player error: {e.details()}"
            ) from e

    # --- lifecycle ---
    def open_ui(self) -> str:
        """Open the TUI if it isn't open (it starts the server). Does not auto-start a second server."""
        self._ui_checked = True
        if not self._open_if_missing():
            return "already open"
        self._connect()
        try:
            grpc.channel_ready_future(self._channel).result(timeout=START_WAIT)
        except grpc.FutureTimeoutError as e:
            raise TermusicError("I opened terminal music but the player didn't come up.") from e
        self._start_tried = True  # the TUI owns the server now
        return "opened"

    def stop_server(self) -> str:
        """Ask the server to quit, then force-kill leftover termusic* processes. Never auto-starts."""
        graceful = False
        try:
            self._connect().QuitServer(pb.Empty(), timeout=RPC_TIMEOUT)
            graceful = True
            time.sleep(0.5)
        except grpc.RpcError:
            pass  # already down, or went away mid-call
        killed = self.killer()
        if self._channel is not None:
            self._channel.close()
        self._channel = self._stub = None
        self._start_tried = False  # allow a later start
        self._ui_checked = False  # reopen the TUI on the next command
        self._ui_opened_at = float("-inf")
        return "stopped" if graceful or killed else "wasn't running"

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
        """Paused: resume. Playing: leave it. Stopped, or just brought up by Evie: start at track 1
        (termusic would otherwise resume wherever it left off)."""
        st = self.status()
        fresh, self._fresh = self._fresh, False
        if st["state"] == "paused" and not fresh:
            self._call("TogglePause")
            return "resumed"
        if st["state"] == "playing" and (not fresh or st["track_index"] == 0):
            return "already playing"
        return self.play_track(1)

    def play_track(self, number: int) -> str:
        """Play queue position `number` (1-based)."""
        tracks = self._call("GetPlaylist").tracks
        if not tracks:
            return "queue is empty"
        if not 1 <= number <= len(tracks):
            return f"the queue has {len(tracks)} tracks"
        self._call("PlaySpecific", pb.PlaylistPlaySpecific(track_index=number - 1, id=tracks[number - 1].id))
        self._fresh = False
        return "playing" if number == 1 else f"playing track {number}"

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
        """Append a file path or URL. Termusic silently ignores tracks it cannot use, so check
        that the queue really grew."""
        n = len(self._call("GetPlaylist").tracks)
        kind = "url" if source.startswith(("http://", "https://")) else "path"
        self._call("AddToPlaylist", pb.PlaylistTracksToAdd(at_index=n, tracks=[pb.TrackId(**{kind: source})]))
        if len(self._call("GetPlaylist").tracks) <= n:
            raise TermusicError("The music player didn't accept that track. It may not be a valid file.")

    def clear(self) -> None:
        self._call("RemoveFromPlaylist", pb.PlaylistTracksToRemove(clear=pb.PlaylistTracksToRemoveClear()))

    def shuffle(self) -> None:
        self._call("ShufflePlaylist")
