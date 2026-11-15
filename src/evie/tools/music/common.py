"""Shared by the music tools: the termusic client and the error-to-sentence wrapper."""
from functools import wraps
from typing import Annotated

from pydantic import Field

from evie.utils import config
from evie.services.music.termusic import Termusic, TermusicError



_client: Termusic | None = None


def set_client(c: Termusic | None) -> None:
    """Swap the client (tests, custom address)."""
    global _client
    _client = c


def _c() -> Termusic:
    global _client
    if _client is None:
        _client = Termusic(show_ui=config.TERMUSIC_SHOW_UI)
    return _client


def _speakable(fn):
    """Turn server errors into a short sentence the model can relay."""
    @wraps(fn)
    def inner(*a, **kw):
        try:
            return fn(*a, **kw)
        except TermusicError as e:
            return str(e)
    return inner


Steps = Annotated[int, Field(ge=1, le=20)]
