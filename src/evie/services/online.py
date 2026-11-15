"""Find and download songs with yt-dlp. Argv lists only, never a shell string."""
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Callable

# Only these hosts can be downloaded; also guarantees the URL cannot start with '-'.
_URL = re.compile(r"^https://((www|music)\.)?(youtube\.com|youtu\.be)/\S+$")
Runner = Callable[..., subprocess.CompletedProcess]


class OnlineError(Exception):
    """Message is safe to read aloud."""


def _exe() -> str:
    exe = shutil.which("yt-dlp")
    if not exe:
        raise OnlineError("I can't find yt-dlp on this PC.")
    return exe


def search(query: str, n: int = 5, run: Runner | None = None) -> list[dict]:
    """Top YouTube results: title, channel, seconds, url."""
    r = (run or subprocess.run)(
        [_exe(), f"ytsearch{n}:{query}", "--flat-playlist", "--dump-json", "--no-warnings"],
        capture_output=True, text=True, timeout=60,
    )
    if r.returncode != 0:
        raise OnlineError("The online search failed.")
    out = []
    for line in r.stdout.splitlines():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        out.append({
            "title": d.get("title", "?"),
            "channel": d.get("channel") or d.get("uploader") or "",
            "seconds": int(d.get("duration") or 0),
            "url": d.get("webpage_url") or f"https://www.youtube.com/watch?v={d.get('id')}",
        })
    return out


def download(url: str, dest: Path, run: Runner | None = None) -> Path:
    """Download audio as opus into `dest` (same naming as the existing library: 'Title [id].opus')."""
    if not _URL.match(url):
        raise OnlineError("I only download from YouTube links.")
    dest.mkdir(parents=True, exist_ok=True)
    r = (run or subprocess.run)(
        [_exe(), "--no-playlist", "-x", "--audio-format", "opus", "--no-warnings",
         "-o", str(dest / "%(title)s [%(id)s].%(ext)s"), "--print", "after_move:filepath", "--", url],
        capture_output=True, text=True, timeout=600,
    )
    lines = [x for x in r.stdout.splitlines() if x.strip()]
    if r.returncode != 0 or not lines:
        raise OnlineError("The download failed.")
    return Path(lines[-1].strip())
