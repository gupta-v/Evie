"""Draft text for the user and leave it on their clipboard."""
from typing import Annotated

from pydantic import Field

from evie.core.registry import tool
from evie.services import clipboard


@tool
def copy_to_clipboard(text: Annotated[str, Field(min_length=1, max_length=2000)]) -> str:
    """Copy text to the user's clipboard so they can paste it. Use this when you draft a message for
    the user (for example a text to a friend, after opening WhatsApp). Write the draft in the user's
    voice, short and natural. Then tell them it is ready on the clipboard and read the draft aloud.
    Never use it to copy anything the user did not ask for or that you did not write for them.

    Args:
        text: The exact text to place on the clipboard.
    """
    try:
        clipboard.copy(text)
    except clipboard.ClipboardError as e:
        return str(e)
    return "copied to clipboard"
