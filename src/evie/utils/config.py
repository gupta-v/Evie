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
SPEAK = os.getenv("EVIE_SPEAK", "0") == "1"  # read replies aloud
VOICE = os.getenv("EVIE_VOICE") or "en-IN-NeerjaNeural"  # any Edge voice name
DEBUG = os.getenv("EVIE_DEBUG", "0") == "1"
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY") or None  # fast web search; keyless fallback is slow
DEFAULT_LOCATION = os.getenv("EVIE_LOCATION") or "Mumbai"  # used when the user does not name a place
MUSIC_DIR = Path(os.getenv("EVIE_MUSIC_DIR") or Path.home() / "Music")
