"""Gemini talker backend (free tier). Manual tool loop."""
import os

from evie.core import prompts
from evie.utils import config
from evie.core import registry


class GeminiProvider:
    def __init__(self, model: str):
        from google import genai
        from google.genai import types

        self.t = types
        self.client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        self.model = model
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

    def stream(self, text: str):
        """Yields reply text as Gemini produces it. Tool calls run between turns, so a reply that needs
        a tool starts speaking only after the tool is done."""
        t = self.t
        self.history.append(t.Content(role="user", parts=[t.Part.from_text(text=text)]))
        for _ in range(config.MAX_TOOL_TURNS):
            parts, calls = [], []
            for chunk in self.client.models.generate_content_stream(model=self.model, contents=self.history, config=self.config):
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
