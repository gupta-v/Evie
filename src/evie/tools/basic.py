import datetime

from evie.core.registry import tool


@tool
def get_time() -> str:
    """Get the current local date and time."""
    return datetime.datetime.now().strftime("%A %d %B %Y, %H:%M")
