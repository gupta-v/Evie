"""Music tools backed by termusic-server. Transport and volume are `fast` (router-eligible)."""
from functools import wraps
from typing import Annotated

from pydantic import Field

from evie import config
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
        _client = Termusic(show_ui=config.TERMUSIC_SHOW_UI)
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


Steps = Annotated[int, Field(ge=1, le=20)]


@tool(fast=True)
@_speakable
def music_start() -> str:
    """Open terminal music: the termusic player window (TUI), which also starts the music server.
    Use when the user says start, open or launch terminal music, termusic or the music player.
    It does not begin playback; use music_play for that."""
    return f"terminal music {_c().open_ui()}"


@tool(fast=True)
@_speakable
def music_stop_player() -> str:
    """Stop and shut down the music player (termusic, 'terminal music'). Use when the user says
    stop, quit, close, kill or shut down termusic or the music player. Not for pausing."""
    return f"music player {_c().stop_server()}"


@tool(fast=True)
@_speakable
def music_play_track(number: Annotated[int, Field(ge=1)]) -> str:
    """Play a specific song in the queue by its position, for example the 3rd song.

    Args:
        number: Queue position, starting at 1.
    """
    return _c().play_track(number)


@tool(fast=True)
@_speakable
def music_play() -> str:
    """Start or resume music playback. If the player was just opened or stopped, begins with the first song."""
    return _c().play()


@tool(fast=True)
@_speakable
def music_pause() -> str:
    """Pause music playback."""
    return _c().pause()


@tool(fast=True)
@_speakable
def music_next() -> str:
    """Skip to the next track."""
    _c().next()
    return "skipped to next"


@tool(fast=True)
@_speakable
def music_previous() -> str:
    """Go back to the previous track."""
    _c().previous()
    return "went to previous"


@tool(fast=True)
@_speakable
def music_volume_up(times: Steps = 1) -> str:
    """Raise music volume. Each step is 5 points.

    Args:
        times: How many 5-point steps. Default 1.
    """
    return f"volume {_c().volume_up(times)}"


@tool(fast=True)
@_speakable
def music_volume_down(times: Steps = 1) -> str:
    """Lower music volume. Each step is 5 points.

    Args:
        times: How many 5-point steps. Default 1.
    """
    return f"volume {_c().volume_down(times)}"


@tool(fast=True)
@_speakable
def music_set_volume(level: Annotated[int, Field(ge=0, le=100)]) -> str:
    """Set music volume to a level from 0 to 100 (rounded to steps of 5).

    Args:
        level: Target volume, 0-100.
    """
    return f"volume {_c().set_volume(level)}"


@tool
@_speakable
def music_status() -> str:
    """Report whether music is playing, the volume and position in the queue."""
    s = _c().status()
    return f"{s['state']}, volume {s['volume']}, track {s['track_index'] + 1}, {s['position_s']}s of {s['total_s']}s"


@tool
@_speakable
def music_queue() -> str:
    """List what is in the music queue."""
    q = _c().queue()
    return "\n".join(f"{i + 1}. {src}" for i, src in enumerate(q)) or "queue is empty"


@tool
@_speakable
def music_shuffle() -> str:
    """Shuffle the music queue."""
    _c().shuffle()
    return "shuffled"


@tool
@_speakable
def music_clear_queue() -> str:
    """Remove every track from the music queue."""
    _c().clear()
    return "queue cleared"


@tool
@_speakable
def music_add(source: Annotated[str, Field(min_length=1)]) -> str:
    """Add a track to the end of the queue by file path or URL.

    Args:
        source: Local file path or http(s) URL.
    """
    _c().add(source)
    return f"added {source}"
