"""Open installed Windows apps by name, using the Start menu list Windows already keeps.

`Get-StartApps` covers Store apps, classic installs and shortcuts, and `explorer.exe
shell:AppsFolder\\<AppID>` launches any of them, so no per-app code is needed. Argv lists only.

shortcut: the list is read once per session; restart Evie (or ask twice after installing an app) to
pick up a new install.
"""
import json
import shutil
import subprocess
from dataclasses import dataclass
from typing import Callable

from evie.utils.text import words

_LIST_CMD = "Get-StartApps | Select-Object Name, AppID | ConvertTo-Json -Compress"


class AppError(Exception):
    """Message is safe to read aloud."""


@dataclass(frozen=True)
class App:
    name: str
    app_id: str


_cache: list[App] | None = None


def list_apps(run: Callable | None = None) -> list[App]:
    global _cache
    if _cache is None:
        ps = shutil.which("powershell") or shutil.which("pwsh")
        if not ps:
            raise AppError("I can't read the list of installed apps on this PC.")
        r = (run or subprocess.run)(
            [ps, "-NoProfile", "-NonInteractive", "-Command", _LIST_CMD],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
        )
        try:
            rows = json.loads(r.stdout)
        except ValueError as e:
            raise AppError("I couldn't read the list of installed apps.") from e
        rows = [rows] if isinstance(rows, dict) else rows
        # web links (e.g. "Steam Support Center") are not apps
        _cache = [App(x["Name"], x["AppID"]) for x in rows if x.get("Name") and not str(x.get("AppID", "")).startswith("http")]
    return _cache


_FILLER = {"windows", "microsoft", "app", "the"}  # "Windows Terminal" is listed as just "Terminal"


def find(query: str, apps: list[App] | None = None) -> list[App]:
    """Apps whose name contains every word of `query`, closest name first."""
    q = [w for w in words(query) if len(w) > 1 and w not in _FILLER] or words(query)
    if not q:
        return []
    hits = []
    for a in apps if apps is not None else list_apps():
        name = words(a.name)
        if all(w in name for w in q):
            hits.append((len(name), a))  # fewer extra words = closer match ("Steam" before "Steam Support")
    return [a for _, a in sorted(hits, key=lambda h: h[0])]


def launch(app: App, popen: Callable | None = None) -> None:
    explorer = shutil.which("explorer")
    if not explorer:
        raise AppError("I can't start apps on this PC.")
    (popen or subprocess.Popen)([explorer, "shell:AppsFolder\\" + app.app_id])
