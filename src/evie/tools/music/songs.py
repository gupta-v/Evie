"""Songs by name from the user's library, and adding by path or URL."""
import os
from pathlib import Path
from typing import Annotated

from pydantic import Field

from evie.core.registry import tool
from evie.services.music import library
from evie.tools.music.common import _c, _speakable
from evie.utils.text import clean_title



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
        return None, "Several songs match, ask the user which one:\n" + _numbered([clean_title(h.title) for h in strong])
    if hits:
        return None, f"No exact match for '{name}'. Close ones, ask if any is right:\n" + _numbered([clean_title(h.title) for h in hits])
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
    return f"{_queue_and_play(song.path)}: {clean_title(song.title)}" if song else msg


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
        return f"already in the queue: {clean_title(song.title)}"
    c.add(str(song.path))
    return f"added to the queue: {clean_title(song.title)}"
