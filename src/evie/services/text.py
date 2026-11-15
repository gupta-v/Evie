"""Turn messy song titles (YouTube titles, yt-dlp file names) into short text that is fine to speak.

Deterministic on purpose: instant, no LLM call, same answer every time. It removes noise such as
"Official Music Video", "Lyrics", channel names after a bar, [video ids] and underscores, and keeps
what helps someone choose between versions ("8D", "slowed & reverb", "feat. X", "Remix").

shortcut: the noise list is hand-written for English/Hindi YouTube titles; add words as new noise
shows up, or let the talker model paraphrase if it ever needs to be smarter.
"""
import re

_NOISE = (
    r"official\s+(?:music\s+|lyric(?:al)?\s+|full\s+)?(?:video|audio|song|visuali[sz]er)"
    r"|(?:music|lyric(?:al)?|full|video|audio)\s+(?:video|song|audio)"
    r"|with\s+lyrics|lyrics?|lyrical|visuali[sz]er|full\s+song|hd|hq|4k|mv"
)
_NOISE_RE = re.compile(rf"\b(?:{_NOISE})\b", re.I)
_BRACKET = re.compile(r"[\(\[\{]([^\)\]\}]*)[\)\]\}]")
_ID = re.compile(r"\s*\[[\w-]{11}\]\s*$")
_BARS = re.compile(r"\s*(?:\|\||\||｜)\s*")  # ASCII bars and the fullwidth bar yt-dlp substitutes
_EDGES = " -,:;|"


def clean_title(raw: str) -> str:
    """Short, speakable version of `raw`. Falls back to `raw` if cleaning would leave nothing."""
    t = _ID.sub("", raw.replace("_", " "))

    def drop_noisy_brackets(m: re.Match) -> str:
        inner = m.group(1)
        return "" if _NOISE_RE.search(inner) and not _NOISE_RE.sub("", inner).strip(" -,") else m.group(0)

    t = _BRACKET.sub(drop_noisy_brackets, t)
    t = _BARS.split(t)[0]  # after the first bar come channel names and tags
    t = _NOISE_RE.sub("", t)
    t = re.sub(r"\(\s*\)|\[\s*\]", "", t)
    t = re.sub(r"\s+", " ", t).strip(_EDGES + " ")
    return t or raw.replace("_", " ").strip()


def spoken_duration(mmss: str) -> str:
    """'04:03' -> '4:03'."""
    m, _, s = mmss.partition(":")
    return f"{int(m)}:{s}" if m.isdigit() and s else mmss
