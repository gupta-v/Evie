"""Open installed Windows apps by name, and web pages in the default browser."""
import re
import webbrowser
from typing import Annotated
from urllib.parse import urlparse

from pydantic import Field

from evie.core.registry import tool
from evie.services import apps
from evie.services.text import words

NOT_A_URL = "That isn't a web address I can open."
_BARE_DOMAIN = re.compile(r"^(?:[\w-]+\.)+[a-z]{2,}(?::\d+)?(?:[/?#]\S*)?$", re.I)  # youtube.com, x.org/a?b=c


@tool
def open_app(name: Annotated[str, Field(min_length=1)]) -> str:
    """Open an installed Windows app by name, for example WhatsApp, Spotify, Discord, Notepad or Steam.
    Use this when the user says open, launch or start an app. For music, use the music tools instead.
    If it reports no match or several matches, tell the user and ask which one.

    Args:
        name: The app's name as the user said it.
    """
    try:
        hits = apps.find(name)
        exact = [a for a in hits if words(a.name) == words(name)]
        chosen = exact[0] if exact else hits[0] if len(hits) == 1 else None
        if chosen is None:
            if hits:
                options = "\n".join(f"{i}. {a.name}" for i, a in enumerate(hits[:5], 1))
                return f"Several apps match '{name}', ask the user which one:\n{options}"
            return f"No installed app matching '{name}'. Tell the user."
        apps.launch(chosen)
        return f"opening {chosen.name}"
    except apps.AppError as e:
        return str(e)


@tool
def open_website(url: Annotated[str, Field(min_length=4)]) -> str:
    """Open a web page in the user's default browser. Use this for websites and web apps such as Gmail
    (https://mail.google.com), Google Calendar (https://calendar.google.com), YouTube, GitHub, or a web
    search (https://www.google.com/search?q=...). Add https:// when the user gives only a name like
    youtube.com. Use open_app instead for installed desktop apps.

    Args:
        url: The full http or https address to open.
    """
    text = url.strip()
    if "://" not in text:
        if not _BARE_DOMAIN.match(text):  # "javascript:x" or "ms-settings:x" must not become https://...
            return NOT_A_URL
        text = "https://" + text
    try:
        u = urlparse(text)
        u.port  # raises ValueError on a malformed port
    except ValueError:
        return NOT_A_URL
    if u.scheme not in ("http", "https") or not u.hostname:  # model text must never launch other protocols
        return NOT_A_URL
    webbrowser.open(u.geturl())  # the user's default browser
    return f"opening {u.hostname}"
