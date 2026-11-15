"""Talker: picks a provider from config, owns the 'stuck' fallback. Heavy work goes to tasks later."""
import re

import evie.tools  # noqa: F401  (registers tools)
from evie.utils import config
from evie.core import registry, router

STUCK = "I got stuck on that one."
YES = re.compile(r"^\W*(yes|yeah|yep|yup|sure|ok|okay|go ahead|do it|confirm|haan)\b", re.I)
NO = re.compile(r"^\W*(no|nope|nah|cancel|don't|do not)\b", re.I)


class Agent:
    def __init__(self):
        if config.PROVIDER == "gemini":
            from evie.providers.gemini import GeminiProvider as P
        elif config.PROVIDER == "anthropic":
            from evie.providers.anthropic import AnthropicProvider as P
        else:
            raise ValueError(f"unknown EVIE_PROVIDER: {config.PROVIDER}")
        self.provider = P(config.MODEL)
        self.pending: tuple[str, dict] | None = None  # a write call waiting for the user's yes

    def respond(self, text: str) -> str:
        """A blocked write tool is remembered; the user's next 'yes' runs it with approval."""
        if self.pending:
            name, args = self.pending
            self.pending = None
            if YES.match(text):
                out = registry.call(name, args, approved=True)
                text = f"The user approved. Result of {name}: {out}. Tell them briefly."
            elif NO.match(text):
                text = "The user declined. Acknowledge briefly."
        else:
            fast = router.route(text)
            if fast:  # fixed command: run the tool, speak its result, skip the LLM
                return registry.call(*fast)
        reply = self.provider.respond(text) or STUCK
        self.pending = registry.take_blocked()
        return reply
