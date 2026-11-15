"""Settings from environment (.env). One place, no scattered os.getenv."""
import os

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
