"""Drive termusic's own YouTube search (the `s` key in the library pane) by typing into its window.

Needs the termusic window in front. Typing into the wrong window would be bad, so the window is
verified first and nothing is typed otherwise. Never use this while a game is running.
"""
import time

from evie.services.termusic import TermusicError

TITLE = "Evie Termusic"  # set by open_tui; the terminal must not let the app overwrite it


def youtube_search(query: str) -> None:
    if not query.isascii():
        raise TermusicError("I can only type plain English letters into termusic.")
    import pyautogui  # heavy: imported on use
    import pygetwindow as gw

    wins = gw.getWindowsWithTitle(TITLE)
    if not wins:
        raise TermusicError("I can't find the termusic window.")
    try:
        wins[0].activate()
    except Exception:  # Windows may refuse focus changes; the check below decides
        pass
    time.sleep(0.4)
    active = gw.getActiveWindow()
    if not active or TITLE not in active.title:
        raise TermusicError("I couldn't bring the termusic window to the front, so I typed nothing.")
    pyautogui.press("s")  # youtube_search key in the library pane
    time.sleep(0.4)
    pyautogui.write(query, interval=0.01)
    pyautogui.press("enter")
