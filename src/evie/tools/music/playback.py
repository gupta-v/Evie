"""Start, stop, pause, skip and inspect the player. Transport tools are `fast` (router-eligible)."""
from typing import Annotated

from pydantic import Field

from evie.core.registry import tool
from evie.tools.music.common import _c, _speakable



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
    """Resume or start whatever is queued. Takes no song name: for a named song use music_play_song."""
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
