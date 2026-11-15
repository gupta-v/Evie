"""Settings from environment (.env). One place, no scattered os.getenv."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROVIDER = os.getenv("EVIE_PROVIDER", "gemini").lower()
_DEFAULT_MODEL = {"gemini": "gemini-3.5-flash-lite", "anthropic": "claude-haiku-5-5"}
MODEL = os.getenv("EVIE_MODEL") or _DEFAULT_MODEL.get(PROVIDER, "")

MAX_TOOL_TURNS = 5
TERMUSIC_ADDR = os.getenv("TERMUSIC_ADDR", "[::1]:5101")
TERMUSIC_AUTOSTART = os.getenv("TERMUSIC_AUTOSTART", "1") == "1"
# Open the termusic TUI window whenever Evie uses music (the TUI also starts the server). Turn off for gaming.
TERMUSIC_SHOW_UI = os.getenv("TERMUSIC_SHOW_UI", "1") == "1"
GROQ_API_KEYS = [k for k in (os.getenv(n) for n in ("GROQ_API_KEY", "GROQ_API_KEY1", "GROQ_API_KEY2")) if k]  # rotated on rate limits
_mic = os.getenv("EVIE_MIC") or None  # input device: index or name part; default is the system default
MIC = int(_mic) if _mic and _mic.isdigit() else _mic
STT_ORDER = [n.strip() for n in (os.getenv("EVIE_STT") or "local,groq").split(",") if n.strip()]  # speech-to-text backends, tried in order
STT_MODEL = os.getenv("EVIE_STT_MODEL") or "base"  # on-device Whisper. base = Hindi+English (Hinglish), ~0.7 s; base.en = English only; small = ~2 s and writes Hindi in Devanagari
STT_LANGS = tuple(x.strip() for x in (os.getenv("EVIE_LANGS") or "en,hi").split(",") if x.strip())  # with EVIE_LANG=auto: speech detected as any other language is treated as noise
MODELS_DIR = Path(__file__).resolve().parents[3] / "models"
STT_LANGUAGE = os.getenv("EVIE_LANG") or "auto"  # "auto" detects (Hinglish); "en" or "hi" forces one language, which stops guesses from noise but breaks Hinglish
THRESHOLD = float(os.getenv("EVIE_THRESHOLD") or 0) or None  # fixed speech level; unset = learn the room
SPEAK = os.getenv("EVIE_SPEAK", "0") == "1"  # read replies aloud
VOICE = os.getenv("EVIE_VOICE") or "en-IN-NeerjaNeural"  # any Edge voice name
TTS_ORDER = [n.strip() for n in (os.getenv("EVIE_TTS") or "kokoro,edge").split(",") if n.strip()]  # tried in order
KOKORO_VOICE = os.getenv("EVIE_KOKORO_VOICE") or "af_sarah"  # e.g. af_heart, af_bella, bf_emma
KOKORO_DIR = MODELS_DIR / "kokoro"
DEBUG = os.getenv("EVIE_DEBUG", "0") == "1"
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY") or None  # fast web search; keyless fallback is slow
DEFAULT_LOCATION = os.getenv("EVIE_LOCATION") or "Mumbai"  # used when the user does not name a place
MUSIC_DIR = Path(os.getenv("EVIE_MUSIC_DIR") or Path.home() / "Music")
