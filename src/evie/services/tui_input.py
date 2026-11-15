"""Drive termusic's own YouTube search (the `s` key in the library pane) from the background.

Keys are written straight into the TUI process's console (see console_input), so the window is not
focused or touched and the keys can only reach termusic. Safe to use while a game is running.
"""
from evie.services import console_input
from evie.services.termusic import TermusicError, tui_pids


def youtube_search(query: str) -> None:
    pids = tui_pids()
    if not pids:
        raise TermusicError("I can't find the termusic window.")
    try:
        # newest TUI; pause so the search box is open before the text arrives
        console_input.send_keys(pids[-1], ["s", *query, console_input.ENTER], pause_after_first=0.4)
    except (RuntimeError, ValueError, OSError) as e:
        raise TermusicError(f"I couldn't type into termusic: {e}") from e
