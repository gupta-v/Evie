"""Gemini talker backend (free tier). Manual tool loop."""
import os
import re
import time

from evie.core import prompts
from evie.utils import config
from evie.core import registry


class GeminiProvider:
    def __init__(self, model: str):
        from google import genai
        from google.genai import types

        self.t = types
        # attempts=1: the library otherwise waits out a free-tier "retry in 24s" silently (9-16 s of nothing)
        self.client = genai.Client(api_key=os.environ["GEMINI_API_KEY"],
                                   http_options=types.HttpOptions(retry_options=types.HttpRetryOptions(attempts=1)))
        self.models = [m.strip() for m in model.split(",") if m.strip()]  # free-tier limits are per model
        self._cool: dict[str, float] = {}  # model -> time until which it is rate limited
        decls = [
            types.FunctionDeclaration(
                name=s["name"],
                description=s["description"],
                # Gemini rejects an empty-properties object schema
                **({"parameters": s["input_schema"]} if s["input_schema"]["properties"] else {}),
            )
            for s in registry.specs()
        ]
        self.config = types.GenerateContentConfig(
            system_instruction=prompts.SYSTEM_PROMPT,
            tools=[types.Tool(function_declarations=decls)],
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            max_output_tokens=512,
        )
        self.history: list = []

    def respond(self, text: str) -> str | None:
        return "".join(self.stream(text)) or None  # None: nothing came back (tool-turn cap hit)

    def _chunks(self):
        """Chunks from the first model that is not rate limited; a 429 sidelines that model and tries the next."""
        from google.genai import errors

        last = None
        for model in self.models:
            if self._cool.get(model, 0) > time.monotonic():
                continue
            try:
                stream = self.client.models.generate_content_stream(model=model, contents=self.history, config=self.config)
                first = next(iter(stream), None)  # a limit shows up here, before any text was spoken
            except errors.ClientError as e:
                if e.code != 429:
                    raise
                wait = re.search(r"retry in ([\d.]+)s", str(e))
                self._cool[model] = time.monotonic() + (float(wait.group(1)) if wait else 30) + 1
                last = e
                continue
            if first is not None:
                yield first
            yield from stream
            return
        raise last or RuntimeError("every Gemini model is rate limited")

    def stream(self, text: str):
        """Yields reply text as Gemini produces it. Tool calls run between turns, so a reply that needs
        a tool starts speaking only after the tool is done."""
        start = len(self.history)
        try:
            yield from self._stream(text)
        except Exception:
            del self.history[start:]  # a failed turn must not leave half a conversation behind
            raise

    def _stream(self, text: str):
        t = self.t
        self.history.append(t.Content(role="user", parts=[t.Part.from_text(text=text)]))
        for _ in range(config.MAX_TOOL_TURNS):
            parts, calls = [], []
            for chunk in self._chunks():
                content = chunk.candidates[0].content if chunk.candidates else None
                for part in (content.parts or []) if content else []:
                    parts.append(part)
                    if part.function_call:
                        calls.append(part.function_call)
                    elif part.text and not part.thought:
                        yield part.text
            self.history.append(t.Content(role="model", parts=parts))
            if not calls:
                return
            responses = [
                t.Part.from_function_response(name=c.name, response={"result": registry.call(c.name, dict(c.args or {}))})
                for c in calls
            ]
            self.history.append(t.Content(role="user", parts=responses))
