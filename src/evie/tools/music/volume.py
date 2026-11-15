"""Volume tools. Each step is 5 points (termusic's own step)."""
from typing import Annotated

from pydantic import Field

from evie.core.registry import tool
from evie.tools.music.common import Steps, _c, _speakable



@tool(fast=True)
@_speakable
def music_volume_up(times: Steps = 1) -> str:
    """Raise music volume. Each step is 5 points.

    Args:
        times: How many 5-point steps. Default 1.
    """
    return f"volume {_c().volume_up(times)}"


@tool(fast=True)
@_speakable
def music_volume_down(times: Steps = 1) -> str:
    """Lower music volume. Each step is 5 points.

    Args:
        times: How many 5-point steps. Default 1.
    """
    return f"volume {_c().volume_down(times)}"


@tool(fast=True)
@_speakable
def music_set_volume(level: Annotated[int, Field(ge=0, le=100)]) -> str:
    """Set music volume to a level from 0 to 100 (rounded to steps of 5).

    Args:
        level: Target volume, 0-100.
    """
    return f"volume {_c().set_volume(level)}"
