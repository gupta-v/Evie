"""Wait for a newly downloaded song to appear in the music folder (termusic downloads there).

shortcut: polls the folder every few seconds and calls the callback once. Fine for one download at a
time; use a filesystem watcher if this ever needs to track many.
"""
import threading
import time
from pathlib import Path
from typing import Callable

from evie.services import library

_cancel = threading.Event()


def watch_new_song(
    on_found: Callable[[Path], None], root: Path | None = None, timeout: float = 300.0, interval: float = 2.0,
    scan: Callable[[], list[Path]] | None = None, sleep=time.sleep, clock=time.monotonic,
) -> threading.Thread:
    """Call `on_found(path)` once, for the first new audio file whose size stops changing.
    Starting a new watch cancels the previous one. Gives up quietly after `timeout` seconds."""
    global _cancel
    _cancel.set()
    cancel = _cancel = threading.Event()
    scan = scan or (lambda: library.scan(root))
    before = set(scan())

    def size(p: Path) -> int:
        try:
            return p.stat().st_size
        except OSError:
            return -1  # vanished: yt-dlp deletes its intermediate file after converting

    def run():
        seen: dict[Path, int] = {}
        end = clock() + timeout
        while clock() < end and not cancel.is_set():
            sleep(interval)
            for p in sorted(set(scan()) - before):
                n = size(p)
                if n > 0 and seen.get(p) == n:  # unchanged since the last poll
                    sleep(interval)  # one more look: a converter may be about to replace it
                    if size(p) == n and not cancel.is_set():
                        on_found(p)
                        return
                seen[p] = n

    t = threading.Thread(target=run, daemon=True)
    t.start()
    return t
