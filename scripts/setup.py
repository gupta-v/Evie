"""One-time setup and health check: `uv run python scripts/setup.py`. Safe to run again.

Downloads the Kokoro voice files if missing, checks keys (names only, never values), the microphone,
and the tools Evie drives. Does not change .env or install anything else.
"""
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

KOKORO_BASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
KOKORO_FILES = {"kokoro-v1.0.int8.onnx": 92_361_271, "voices-v1.0.bin": 28_214_398}  # name: exact size in bytes


def line(ok: bool | None, msg: str) -> None:
    print(f"[{'ok' if ok else 'MISSING' if ok is False else 'note'}] {msg}")


def kokoro() -> None:
    import httpx

    dest = ROOT / "models" / "kokoro"
    dest.mkdir(parents=True, exist_ok=True)
    for name, size in KOKORO_FILES.items():
        path = dest / name
        if path.is_file() and path.stat().st_size == size:
            line(True, f"voice file {name}")
            continue
        print(f"      downloading {name} ({size // 1_000_000} MB) ...")
        tmp = path.with_suffix(path.suffix + ".part")
        with httpx.stream("GET", KOKORO_BASE + name, follow_redirects=True, timeout=60) as r:
            r.raise_for_status()
            with tmp.open("wb") as f:
                for chunk in r.iter_bytes(1 << 20):
                    f.write(chunk)
        if tmp.stat().st_size != size:
            tmp.unlink()
            line(False, f"{name}: download was the wrong size, try again")
            continue
        tmp.replace(path)
        line(True, f"voice file {name}")


def keys() -> None:
    env = ROOT / ".env"
    if not env.is_file():
        example = ROOT / ".env.example"
        if example.is_file():
            shutil.copy(example, env)
            line(None, "created .env from .env.example: put your keys in it")
        else:
            line(False, ".env (create it and add your keys)")
            return
    names = {ln.split("=", 1)[0].strip() for ln in env.read_text(encoding="utf-8").splitlines() if "=" in ln and not ln.lstrip().startswith("#")}
    values = {n for n in names if os.getenv(n) or any(ln.startswith(n + "=") and ln.split("=", 1)[1].strip() for ln in env.read_text(encoding="utf-8").splitlines())}
    for label, options in [("an LLM key (GEMINI_API_KEY)", ["GEMINI_API_KEY"]), ("a Groq key for speech input (GROQ_API_KEY, _KEY1, _KEY2)", ["GROQ_API_KEY", "GROQ_API_KEY1", "GROQ_API_KEY2"])]:
        line(any(o in values for o in options), label)
    line(None if "TAVILY_API_KEY" not in values else True, "TAVILY_API_KEY (optional: faster web search)")


def machine() -> None:
    try:
        import sounddevice as sd

        mic = sd.query_devices(kind="input")["name"]
        line(True, f"default microphone: {mic} (change with EVIE_MIC, see scripts/mic_check.py)")
    except Exception as e:
        line(False, f"microphone ({e})")
    line(bool(shutil.which("termusic")), "termusic on PATH (music tools)")
    line(bool(shutil.which("wt")), "Windows Terminal 'wt' (music window opens in it)")
    line(bool(shutil.which("clip")), "clip (clipboard tool)")


if __name__ == "__main__":
    keys()
    kokoro()
    machine()
    print("\nNext: uv run evie        (text)\n      uv run evie --voice  (talk)")
