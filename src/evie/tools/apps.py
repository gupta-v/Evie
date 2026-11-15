"""Open installed Windows apps by name."""
from typing import Annotated

from pydantic import Field

from evie.core.registry import tool
from evie.services import apps
from evie.services.text import words


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
