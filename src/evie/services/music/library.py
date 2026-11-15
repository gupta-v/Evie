"""Local music library: find songs by name in the music folder (file names like 'Title - Artist.flac').

shortcut: matches on whole words in the file name and rescans the folder every call; add a cache
or tag reading if the library grows past a few thousand files or names stop carrying the title.
"""
import re
from dataclasses import dataclass
from pathlib import Path

from evie.utils import config
from evie.utils.text import words

EXTS = {".mp3", ".flac", ".opus", ".m4a", ".ogg", ".wav", ".aac", ".wma"}


@dataclass(frozen=True)
class Match:
    path: Path
    hit: float  # share of the query's words found in the file name; 1.0 = all of them
    cover: float  # share of the file name's words that the query covers (prefers tight titles)

    @property
    def title(self) -> str:
        return self.path.stem


_words = words

def scan(root: Path | None = None) -> list[Path]:
    root = Path(root or config.MUSIC_DIR)
    return [p for p in root.rglob("*") if p.suffix.lower() in EXTS] if root.is_dir() else []


def search(query: str, root: Path | None = None, limit: int = 5) -> list[Match]:
    """Best matches first. Needs at least half the query's words in the file name."""
    q = _words(query)
    q = [w for w in q if len(w) > 1] or q  # drop stray one-letter words like "i" or "a"
    if not q:
        return []
    out = []
    for p in scan(root):
        name = _words(p.stem)
        hit = sum(1 for w in q if w in set(name)) / len(q)
        if hit >= 0.5:
            out.append(Match(p, hit, min(len(q) / max(len(name), 1), 1.0)))
    out.sort(key=lambda m: (m.hit, m.cover), reverse=True)
    return out[:limit]


def vocab_hint(root: Path | None = None, max_chars: int = 400) -> str:
    """The library's most common artists, then song titles, as one line of names. Fed to speech-to-text
    so Whisper spells "Anuv Jain" or "Arz Kiya Hai" the way the files do instead of guessing English words."""
    from collections import Counter

    from evie.utils.text import clean_title

    artists, titles = Counter(), []
    for p in scan(root):
        title, _, who = p.stem.rpartition(" - ")
        if not title:
            title, who = p.stem, ""
        for a in who.split(","):
            if a.strip():
                artists[a.strip()] += 1
        titles.append(clean_title(title))
    names = [a for a, _ in artists.most_common(25)] + titles
    out = []
    for n in dict.fromkeys(names):  # unique, keeps order
        if sum(len(x) + 2 for x in out) + len(n) > max_chars:
            break
        out.append(n)
    return ", ".join(out)


_names_cache: dict[str, tuple[float, dict[str, str]]] = {}


def _names(root: Path | None = None) -> dict[str, str]:
    """{letters-only lowercase key: proper spelling} for every artist and short title in the library (1 min cache)."""
    import time

    from evie.utils.text import clean_title

    k = str(root or config.MUSIC_DIR)
    if k in _names_cache and time.monotonic() - _names_cache[k][0] < 60:
        return _names_cache[k][1]
    out: dict[str, str] = {}
    for p in scan(root):
        title, _, who = p.stem.rpartition(" - ")
        if not title:
            title, who = p.stem, ""
        for name in [clean_title(title), *[a.strip() for a in who.split(",")]]:
            key = re.sub(r"[^a-z0-9]", "", name.lower())
            if len(key) >= 5 and len(name.split()) <= 4:
                out.setdefault(key, name)
    _names_cache[k] = (time.monotonic(), out)
    return out


def correct(text: str, root: Path | None = None, cutoff: float = 0.82) -> str:
    """Snap near-miss names in speech-to-text output to the library's spelling: "Anubjain" or "Anup Jain"
    become "Anuv Jain", "Le Jyotum Mereho" becomes "Jo Tum Mere Ho". Windows of 3, 2 and 1 words are compared
    on letters only; at least 5 letters and a close match (difflib ratio >= cutoff), so ordinary words stay.

    shortcut: spelling similarity only (no phonetics), and a name must be in the library to be fixed."""
    import difflib

    names = _names(root)
    keys = list(names)
    words, out, i = text.split(), [], 0
    while i < len(words):
        for n in (3, 2, 1):
            chunk = words[i:i + n]
            key = re.sub(r"[^a-z0-9]", "", " ".join(chunk).lower())
            if len(chunk) < n or len(key) < 5:
                continue
            hit = key if key in names else next(iter(difflib.get_close_matches(key, keys, 1, cutoff)), None)
            if hit:
                tail = re.search(r"[.,!?]+$", chunk[-1])
                out.append(names[hit] + (tail.group() if tail else ""))
                i += n
                break
        else:
            out.append(words[i])
            i += 1
    return " ".join(out)
