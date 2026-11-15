"""Songs the library lacks: termusic's own online search and download, then queue and play."""
from pathlib import Path
from typing import Annotated

from pydantic import Field

from evie.core.registry import tool
from evie.services.music import tui_input, watcher
from evie.services.music.termusic import TermusicError
from evie.tools.music.common import _c, _speakable
from evie.tools.music.songs import _queue_and_play
from evie.utils.text import clean_title, spoken_duration




def _announce(msg: str) -> None:
    print("[Evie]", msg)  # shortcut: stdout until voice/notify exists


def _on_downloaded(path: Path) -> None:
    try:
        played = _queue_and_play(path)
        _announce(f"Downloaded {clean_title(path.stem)}. " + ("Now playing it." if played.startswith("playing") else played))
    except TermusicError as e:
        _announce(str(e))


@tool
@_speakable
def music_search_online(query: Annotated[str, Field(min_length=1)]) -> str:
    """Search YouTube with termusic's own search for a song the library does not have, only after the
    user agrees to search. Returns numbered results: read the first few aloud (number, title, length)
    and ask which one to add, then call music_pick_result with that number. If this reports an error,
    say what it said and stop; do not try another way to download.

    Args:
        query: Song title and artist to search for.
    """
    _c().open_ui()
    results = tui_input.search(query)
    return "\n".join(f"{r.number}. {clean_title(r.title)} ({spoken_duration(r.duration)})" for r in results)


@tool
@_speakable
def music_pick_result(number: Annotated[int, Field(ge=1)]) -> str:
    """Choose one of the numbered results from music_search_online. termusic downloads it, and Evie
    adds it to the queue and plays it once it has arrived.

    Args:
        number: The result number the user chose.
    """
    watcher.watch_new_song(_on_downloaded)  # snapshot the folder before the download starts
    try:
        chosen = tui_input.pick(number)
    except TermusicError:
        watcher.cancel()
        raise
    return f"Downloading {clean_title(chosen.title)}. It will play when it is ready."
