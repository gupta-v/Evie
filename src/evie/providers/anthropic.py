"""Claude talker backend. Needs API credits (not a Pro subscription)."""
from evie import config
from evie.core import registry


class AnthropicProvider:
    def __init__(self, model: str):
        from anthropic import Anthropic

        self.client = Anthropic()
        self.model = model
        self.history: list[dict] = []

    def respond(self, text: str) -> str | None:
        self.history.append({"role": "user", "content": text})
        for _ in range(config.MAX_TOOL_TURNS):
            msg = self.client.messages.create(
                model=self.model, max_tokens=512, system=config.SYSTEM_PROMPT,
                tools=registry.specs(), messages=self.history,
            )
            self.history.append({"role": "assistant", "content": msg.content})
            if msg.stop_reason != "tool_use":
                return "".join(b.text for b in msg.content if b.type == "text")
            results = [
                {"type": "tool_result", "tool_use_id": b.id, "content": registry.call(b.name, b.input)}
                for b in msg.content if b.type == "tool_use"
            ]
            self.history.append({"role": "user", "content": results})
        return None
