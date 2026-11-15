"""Music tools backed by termusic-server. Transport and volume are `fast` (router-eligible)."""
import os
from functools import wraps
from pathlib import Path
from typing import Annotated

from pydantic import Field

from evie import config
from evie.core.registry import tool
from evie.services import library, online
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
    """Add a track to the queue by an exact file path or http(s) URL. This is not for song names:
    when the user names a song use music_queue_song.

    Args:
        source: Local file path or http(s) URL.
    """
    if not source.startswith(("http://", "https://")) and not os.path.isfile(source):
        return "That is not a file or link. For a song name, use music_queue_song."
    _c().add(source)
    return f"added {source}"


# --- songs by name: library first, then online with the user's say-so ---

def _queue_and_play(path: Path) -> str:
    c = _c()
    queue = [os.path.normcase(os.path.normpath(q)) for q in c.queue()]
    key = os.path.normcase(os.path.normpath(str(path)))
    if key not in queue:
        c.add(str(path))
        queue.append(key)
    return c.play_track(queue.index(key) + 1)


def _numbered(items: list[str]) -> str:
    return "\n".join(f"{i}. {t}" for i, t in enumerate(items, 1))


def _resolve(name: str):
    """One library song for `name`, or (None, a message telling the model what to say)."""
    hits = library.search(name)
    strong = [h for h in hits if h.hit == 1.0]
    if len(strong) == 1:
        return strong[0], ""
    if strong:
        return None, "Several songs match, ask the user which one:\n" + _numbered([h.title for h in strong])
    if hits:
        return None, f"No exact match for '{name}'. Close ones, ask if any is right:\n" + _numbered([h.title for h in hits])
    return None, f"No song matching '{name}' in the library. Tell the user and ask if they want you to search online."


@tool(fast=True)
@_speakable
def music_play_song(name: Annotated[str, Field(min_length=1)]) -> str:
    """Play a song by name from the user's music library, adding it to the queue if needed.
    Use this whenever the user names a song, artist or phrase to play. If it reports no match,
    tell the user the song was not found and offer to search online. Never claim a song is playing
    unless this tool says so.

    Args:
        name: Song title, optionally with the artist.
    """
    song, msg = _resolve(name)
    return f"{_queue_and_play(song.path)}: {song.title}" if song else msg


@tool
@_speakable
def music_queue_song(name: Annotated[str, Field(min_length=1)]) -> str:
    """Add a song to the end of the queue by name from the user's music library, without playing it.
    Use this when the user says add, queue or put a named song in the queue. If it reports no match,
    tell the user the song was not found and offer to search online. Never claim a song was added
    unless this tool says so.

    Args:
        name: Song title, optionally with the artist.
    """
    song, msg = _resolve(name)
    if not song:
        return msg
    c = _c()
    key = os.path.normcase(os.path.normpath(str(song.path)))
    if key in [os.path.normcase(os.path.normpath(q)) for q in c.queue()]:
        return f"already in the queue: {song.title}"
    c.add(str(song.path))
    return f"added to the queue: {song.title}"


@tool
@_speakable
def music_search_online(query: Annotated[str, Field(min_length=1)]) -> str:
    """Search YouTube for a song the library does not have, only after the user agrees to search.
    Returns numbered options; read the first few to the user and ask which one to add.

    Args:
        query: Song title and artist to search for.
    """
    try:
        results = online.search(query)
    except online.OnlineError as e:
        return str(e)
    if not results:
        return "No online results."
    return _numbered([f"{r['title']} by {r['channel']} ({r['seconds'] // 60}:{r['seconds'] % 60:02d}) {r['url']}" for r in results])


@tool(risk="write")
@_speakable
def music_download(url: Annotated[str, Field(min_length=1)], title: Annotated[str, Field(min_length=1)]) -> str:
    """Download a chosen online result into the user's music library, add it to the queue and play it.
    Only call with a url from music_search_online that the user picked.

    Args:
        url: The YouTube link of the chosen result.
        title: The title of the chosen result, for confirming with the user.
    """
    try:
        path = online.download(url, config.MUSIC_DIR)
    except online.OnlineError as e:
        return str(e)
    return f"downloaded {path.stem}. {_queue_and_play(path)}"
