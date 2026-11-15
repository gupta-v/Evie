"""Drive termusic's own YouTube search (the `s` key in the library pane) from the background.

Keys are written into the TUI process's console and its screen text is read back (see
console_input), so the window is never focused or touched, the keys can only reach termusic, and it
is safe while a game runs. Built for voice: Evie reads the results aloud and presses the one the
user names.

shortcut: results are scraped from the screen (termusic has no API for them), so a termusic UI
redesign can break the parser; the tests pin the layout with a real capture.
"""
import re
import time
from dataclasses import dataclass

from evie.services.music import console_input as ci
from evie.services.music.termusic import TermusicError, tui_pids

# A result row inside the popup: left border, optional selection marker, [duration], title, right border.
_ROW = re.compile(r"│[▶ ]?\[(\d{1,3}:\d{2})\]\s+(.*?)\s*│")
_HEADER = "switch pages"  # the popup's top border says "Tab/Shift+Tab switch pages"
SEARCH_WAIT = 20.0


@dataclass(frozen=True)
class Result:
    number: int  # 1-based, as spoken to the user
    duration: str
    title: str


def parse_results(screen: list[str]) -> tuple[list[Result], int]:
    """(results, index of the highlighted one) from the screen rows. Empty if no search popup is open.
    Only rows below the popup header count, so the playlist pane's [mm:ss] rows are ignored."""
    start = next((i for i, line in enumerate(screen) if _HEADER in line), None)
    if start is None:
        return [], 0
    results, selected = [], 0
    for line in screen[start + 1 :]:
        m = _ROW.search(line)
        if not m:
            if results:
                break
            continue  # the "Duration  Name" column header sits between the border and the rows
        if "▶" in line[: m.start() + 2]:
            selected = len(results)
        results.append(Result(len(results) + 1, m.group(1), m.group(2)))
    return results, selected


def _pid() -> int:
    pids = tui_pids()
    if not pids:
        raise TermusicError("I can't find the termusic window.")
    return pids[-1]  # newest TUI


def _screen(pid: int) -> list[str]:
    try:
        return ci.read_screen(pid)
    except (RuntimeError, OSError, ValueError) as e:
        raise TermusicError(f"I couldn't read termusic's screen: {e}") from e


def _send(pid: int, keys: list[str], pause: float = 0.0) -> None:
    try:
        ci.send_keys(pid, keys, pause_after_first=pause)
    except (RuntimeError, ValueError, OSError) as e:
        raise TermusicError(f"I couldn't type into termusic: {e}") from e


def search(query: str) -> list[Result]:
    """Run termusic's YouTube search and return what it lists. Raises if nothing comes back."""
    pid = _pid()
    if parse_results(_screen(pid))[0]:  # an old search box is still open
        _send(pid, [ci.ESC])
    _send(pid, ["s", *query, ci.ENTER], pause=0.4)
    deadline = time.monotonic() + SEARCH_WAIT
    while time.monotonic() < deadline:
        time.sleep(1)
        results, _ = parse_results(_screen(pid))
        if results:
            return results
    raise TermusicError("termusic's search didn't show any results.")


def pick(number: int) -> Result:
    """Press the `number`th result in the open search box (termusic then downloads it)."""
    pid = _pid()
    results, selected = parse_results(_screen(pid))
    if not results:
        raise TermusicError("The search results aren't open any more. Search again.")
    if not 1 <= number <= len(results):
        raise TermusicError(f"There are only {len(results)} results.")
    move = number - 1 - selected
    _send(pid, [ci.DOWN if move > 0 else ci.UP] * abs(move) + [ci.ENTER])
    return results[number - 1]
