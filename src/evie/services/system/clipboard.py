"""Put text on the Windows clipboard so the user can paste it (e.g. a drafted message)."""
import subprocess


class ClipboardError(Exception):
    """Message is safe to read aloud."""


def copy(text: str) -> None:
    # clip.exe reads UTF-16 with a BOM correctly (plain stdin would mangle emoji and non-ASCII); argv list, no shell
    try:
        subprocess.run(["clip"], input=b"\xff\xfe" + text.encode("utf-16-le"), check=True, timeout=5)
    except (OSError, subprocess.SubprocessError) as e:
        raise ClipboardError("I couldn't reach the clipboard.") from e
