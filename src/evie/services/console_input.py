"""Type into another process's console without focusing its window (Windows).

Attaches to the target's console and writes key events into its input buffer, so the keys can only
reach that process: never the foreground window, never a game. The attach changes this process's own
console, so the work runs in a short-lived child (`python -m evie.services.console_input PID`) and
the key list is sent as JSON on stdin.
"""
import json
import subprocess
import sys
import time

KEY_EVENT, SHIFT_PRESSED, ENHANCED = 1, 0x10, 0x100  # arrows are "enhanced" keys on a real keyboard
ENTER, ESC, DOWN, UP = "<enter>", "<esc>", "<down>", "<up>"
_NAMED = {ENTER: (0x0D, "\r", 0), ESC: (0x1B, "\x1b", 0), DOWN: (0x28, "\0", ENHANCED), UP: (0x26, "\0", ENHANCED)}


def key_records(keys: list[str]) -> list[tuple[bool, int, int, str, int]]:
    """(down, virtual key, scan code, char, control-key state) per key event, down then up.
    `keys` items are single characters or ENTER."""
    import ctypes

    u32 = ctypes.windll.user32
    out = []
    for k in keys:
        if k in _NAMED:
            vk, ch, ctrl = _NAMED[k]
        else:
            if len(k) != 1:
                raise ValueError(f"not a single key: {k!r}")
            scan = u32.VkKeyScanW(ord(k))
            if scan == -1:
                raise ValueError(f"cannot type {k!r} on this keyboard layout")
            vk, ch, ctrl = scan & 0xFF, k, SHIFT_PRESSED if scan & 0x100 else 0
        sc = u32.MapVirtualKeyW(vk, 0)
        out += [(True, vk, sc, ch, ctrl), (False, vk, sc, ch, ctrl)]
    return out


def _write(pid: int, keys: list[str]) -> None:
    import ctypes
    from ctypes import wintypes as w

    class KeyEvent(ctypes.Structure):
        _fields_ = [("down", w.BOOL), ("repeat", w.WORD), ("vk", w.WORD), ("scan", w.WORD),
                    ("char", w.WCHAR), ("ctrl", w.DWORD)]

    class Event(ctypes.Union):
        _fields_ = [("key", KeyEvent), ("pad", ctypes.c_byte * 16)]

    class InputRecord(ctypes.Structure):
        _fields_ = [("type", w.WORD), ("event", Event)]

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.FreeConsole()
    if not k32.AttachConsole(pid):
        raise OSError(f"cannot attach to console of pid {pid} (error {ctypes.get_last_error()})")
    k32.CreateFileW.restype = w.HANDLE
    h = k32.CreateFileW("CONIN$", 0xC0000000, 3, None, 3, 0, None)  # GENERIC_READ|WRITE, SHARE_READ|WRITE, OPEN_EXISTING
    if h in (None, w.HANDLE(-1).value):
        raise OSError("cannot open the console input")
    events = key_records(keys)  # two per key: down and up
    recs = (InputRecord * len(events))()
    for r, (down, vk, sc, ch, ctrl) in zip(recs, events):
        r.type, r.event.key = KEY_EVENT, KeyEvent(down, 1, vk, sc, ch, ctrl)
    done = w.DWORD()
    if not k32.WriteConsoleInputW(h, recs, len(events), ctypes.byref(done)) or done.value != len(events):
        raise OSError("writing to the console input failed")


def _read(pid: int) -> list[str]:
    import ctypes
    from ctypes import wintypes as w

    class Coord(ctypes.Structure):
        _fields_ = [("X", ctypes.c_short), ("Y", ctypes.c_short)]

    class Rect(ctypes.Structure):
        _fields_ = [("Left", ctypes.c_short), ("Top", ctypes.c_short), ("Right", ctypes.c_short), ("Bottom", ctypes.c_short)]

    class Info(ctypes.Structure):
        _fields_ = [("size", Coord), ("cursor", Coord), ("attr", w.WORD), ("window", Rect), ("maxsize", Coord)]

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.FreeConsole()
    if not k32.AttachConsole(pid):
        raise OSError(f"cannot attach to console of pid {pid} (error {ctypes.get_last_error()})")
    k32.CreateFileW.restype = w.HANDLE
    h = k32.CreateFileW("CONOUT$", 0xC0000000, 3, None, 3, 0, None)
    info = Info()
    if not k32.GetConsoleScreenBufferInfo(h, ctypes.byref(info)):
        raise OSError("cannot read the console screen")
    win = info.window
    width, lines = win.Right - win.Left + 1, []
    for y in range(win.Top, win.Bottom + 1):
        buf, n = ctypes.create_unicode_buffer(width), w.DWORD()
        k32.ReadConsoleOutputCharacterW(h, buf, width, Coord(win.Left, y), ctypes.byref(n))
        lines.append(buf.value.rstrip())
    return lines


def read_screen(pid: int) -> list[str]:
    """The visible text of process `pid`'s console, one string per row."""
    r = subprocess.run(
        [sys.executable, "-m", "evie.services.console_input", "read", str(pid)], capture_output=True, text=True, timeout=15
    )
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip().splitlines()[-1] if r.stderr.strip() else "reading the screen failed")
    return json.loads(r.stdout)


def send_keys(pid: int, keys: list[str], pause_after_first: float = 0.0) -> None:
    """Type `keys` into process `pid`'s console. Raises RuntimeError if it could not be done."""
    batches = [keys[:1], keys[1:]] if pause_after_first and len(keys) > 1 else [keys]
    for i, batch in enumerate(batches):
        r = subprocess.run(
            [sys.executable, "-m", "evie.services.console_input", "keys", str(pid)],
            input=json.dumps(batch), capture_output=True, text=True, timeout=15,
        )
        if r.returncode != 0:
            raise RuntimeError(r.stderr.strip().splitlines()[-1] if r.stderr.strip() else "key injection failed")
        if i == 0 and len(batches) > 1:
            time.sleep(pause_after_first)


if __name__ == "__main__":
    if sys.argv[1] == "read":
        print(json.dumps(_read(int(sys.argv[2]))))
    else:
        _write(int(sys.argv[2]), json.load(sys.stdin))
