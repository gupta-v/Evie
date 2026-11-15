"""Settings from environment (.env). One place, no scattered os.getenv."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROVIDER = os.getenv("EVIE_PROVIDER", "gemini").lower()
_DEFAULT_MODEL = {"gemini": "gemini-3.5-flash-lite", "anthropic": "claude-haiku-5-5"}
MODEL = os.getenv("EVIE_MODEL") or _DEFAULT_MODEL.get(PROVIDER, "")

SYSTEM_PROMPT = (
    "You are Evie, a concise voice assistant. Replies are spoken aloud: "
    "one or two short sentences, no markdown. Use tools for actions and facts."
)
MAX_TOOL_TURNS = 5
TERMUSIC_ADDR = os.getenv("TERMUSIC_ADDR", "[::1]:5101")
TERMUSIC_AUTOSTART = os.getenv("TERMUSIC_AUTOSTART", "1") == "1"
# Open the termusic TUI window whenever Evie uses music (the TUI also starts the server). Turn off for gaming.
TERMUSIC_SHOW_UI = os.getenv("TERMUSIC_SHOW_UI", "1") == "1"
DEBUG = os.getenv("EVIE_DEBUG", "0") == "1"
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY") or None  # fast web search; keyless fallback is slow
DEFAULT_LOCATION = os.getenv("EVIE_LOCATION") or "Mumbai"  # used when the user does not name a place
MUSIC_DIR = Path(os.getenv("EVIE_MUSIC_DIR") or Path.home() / "Music")
