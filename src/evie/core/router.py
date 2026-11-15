"""Fast router: exact short commands run their tool directly, no LLM (instant, works offline).

Only whole-sentence matches count, so "play hola amigo" or "next song by arijit" fall through to the
LLM. The reply is the tool's own result.

shortcut: English phrases only, and the model never sees these turns in its history; widen the table
or feed the turns back when that matters.
"""
import re

PREFIX = r"^\W*(?:(?:please|hey evie|evie)\W+)*"
SUFFIX = r"(?:\W+(?:please|now|for me))*\W*$"
_NUM = r"(100|\d{1,2})"


def _rule(body: str) -> re.Pattern:
    return re.compile(PREFIX + body + SUFFIX, re.I)


_RULES: list[tuple[re.Pattern, str, "callable"]] = [
    (_rule(r"(?:pause|stop|hold)(?:\s+(?:the\s+)?(?:music|song|playback))?"), "music_pause", lambda m: {}),
    (_rule(r"(?:play|resume|continue|unpause)(?:\s+(?:the\s+)?(?:music|song|playback))?"), "music_play", lambda m: {}),
    (_rule(r"(?:next|skip)(?:\s+(?:the\s+)?(?:song|track))?"), "music_next", lambda m: {}),
    (_rule(r"(?:previous|go back|back)(?:\s+(?:song|track))?"), "music_previous", lambda m: {}),
    (_rule(rf"(?:volume|vol)\s+(?:to\s+)?{_NUM}"), "music_set_volume", lambda m: {"level": int(m[1])}),
    (_rule(rf"set\s+(?:the\s+)?volume\s+(?:to\s+|at\s+)?{_NUM}"), "music_set_volume", lambda m: {"level": int(m[1])}),
    (_rule(r"(?:volume\s+up|louder|turn\s+it\s+up)"), "music_volume_up", lambda m: {}),
    (_rule(r"(?:volume\s+down|quieter|softer|turn\s+it\s+down)"), "music_volume_down", lambda m: {}),
    (_rule(r"(?:shuffle)(?:\s+(?:the\s+)?(?:music|queue))?"), "music_shuffle", lambda m: {}),
]


def route(text: str) -> tuple[str, dict] | None:
    """(tool name, args) when `text` is a fixed command, else None."""
    for pattern, name, args in _RULES:
        m = pattern.match(text.strip())
        if m:
            return name, args(m)
    return None
