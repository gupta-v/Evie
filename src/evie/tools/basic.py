import datetime

from evie.core.registry import tool


@tool("get_time", "Get the current local date and time.", {})
def get_time() -> str:
    return datetime.datetime.now().strftime("%A %d %B %Y, %H:%M")
