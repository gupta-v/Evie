"""Music tools backed by termusic-server. Transport and volume are `fast` (router-eligible)."""
from functools import wraps

from evie.core.registry import tool
from evie.services.termusic import Termusic, TermusicError

_client: Termusic | None = None


def set_client(c: Termusic | None) -> None:
    """Swap the client (tests, custom address)."""
    global _client
    _client = c


def _c() -> Termusic:
    global _client
    if _client is None:
        _client = Termusic()
    return _client


def _speakable(fn):
    """Turn server errors into a short sentence the model can relay."""
    @wraps(fn)
    def inner(*a, **kw):
        try:
            return fn(*a, **kw)
        except TermusicError as e:
            return str(e)
    return inner


_TIMES = {"times": {"type": "integer", "description": "How many 5-point steps. Default 1."}}


@tool(
    "music_start",
    "Start the music player (termusic, 'terminal music', the music app) if it is not running, then play. "
    "Use when the user says start, open or launch terminal music, termusic or the music player.",
    {},
    fast=True,
)
@_speakable
def music_start() -> str:
    _c().status()  # a down server is started by the client on first call
    return _c().play()


@tool(
    "music_stop_player",
    "Stop and shut down the music player (termusic, 'terminal music'). Use when the user says "
    "stop, quit, close, kill or shut down termusic or the music player. Not for pausing.",
    {},
    fast=True,
)
@_speakable
def music_stop_player() -> str:
    return f"music player {_c().stop_server()}"


@tool("music_play", "Start or resume music playback.", {}, fast=True)
@_speakable
def music_play() -> str:
    return _c().play()


@tool("music_pause", "Pause music playback.", {}, fast=True)
@_speakable
def music_pause() -> str:
    return _c().pause()


@tool("music_next", "Skip to the next track.", {}, fast=True)
@_speakable
def music_next() -> str:
    _c().next()
    return "skipped to next"


@tool("music_previous", "Go back to the previous track.", {}, fast=True)
@_speakable
def music_previous() -> str:
    _c().previous()
    return "went to previous"


@tool("music_volume_up", "Raise music volume. Each step is 5 points.", _TIMES, fast=True, optional=("times",))
@_speakable
def music_volume_up(times: int = 1) -> str:
    return f"volume {_c().volume_up(times)}"


@tool("music_volume_down", "Lower music volume. Each step is 5 points.", _TIMES, fast=True, optional=("times",))
@_speakable
def music_volume_down(times: int = 1) -> str:
    return f"volume {_c().volume_down(times)}"


@tool(
    "music_set_volume",
    "Set music volume to a level from 0 to 100 (rounded to steps of 5).",
    {"level": {"type": "integer", "description": "Target volume, 0-100."}},
    fast=True,
)
@_speakable
def music_set_volume(level: int) -> str:
    return f"volume {_c().set_volume(level)}"


@tool("music_status", "Report whether music is playing, the volume and position in the queue.", {})
@_speakable
def music_status() -> str:
    s = _c().status()
    return f"{s['state']}, volume {s['volume']}, track {s['track_index'] + 1}, {s['position_s']}s of {s['total_s']}s"


@tool("music_queue", "List what is in the music queue.", {})
@_speakable
def music_queue() -> str:
    q = _c().queue()
    return "\n".join(f"{i + 1}. {src}" for i, src in enumerate(q)) or "queue is empty"


@tool("music_shuffle", "Shuffle the music queue.", {})
@_speakable
def music_shuffle() -> str:
    _c().shuffle()
    return "shuffled"


@tool("music_clear_queue", "Remove every track from the music queue.", {})
@_speakable
def music_clear_queue() -> str:
    _c().clear()
    return "queue cleared"


@tool(
    "music_add",
    "Add a track to the end of the queue by file path or URL.",
    {"source": {"type": "string", "description": "Local file path or http(s) URL."}},
)
@_speakable
def music_add(source: str) -> str:
    _c().add(source)
    return f"added {source}"
