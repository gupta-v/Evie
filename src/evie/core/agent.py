"""Talker: picks a provider from config, owns the 'stuck' fallback. Heavy work goes to tasks later."""
from evie import config
import evie.tools  # noqa: F401  (registers tools)

STUCK = "I got stuck on that one."


class Agent:
    def __init__(self):
        if config.PROVIDER == "gemini":
            from evie.providers.gemini import GeminiProvider as P
        elif config.PROVIDER == "anthropic":
            from evie.providers.anthropic import AnthropicProvider as P
        else:
            raise ValueError(f"unknown EVIE_PROVIDER: {config.PROVIDER}")
        self.provider = P(config.MODEL)

    def respond(self, text: str) -> str:
        return self.provider.respond(text) or STUCK
