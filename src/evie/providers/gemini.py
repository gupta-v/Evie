"""Gemini talker backend (free tier). Manual tool loop."""
import os

from evie import config
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
            system_instruction=config.SYSTEM_PROMPT,
            tools=[types.Tool(function_declarations=decls)],
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            max_output_tokens=512,
        )
        self.history: list = []

    def respond(self, text: str) -> str | None:
        t = self.t
        self.history.append(t.Content(role="user", parts=[t.Part.from_text(text=text)]))
        for _ in range(config.MAX_TOOL_TURNS):
            resp = self.client.models.generate_content(
                model=self.model, contents=self.history, config=self.config
            )
            self.history.append(resp.candidates[0].content)
            calls = resp.function_calls
            if not calls:
                return resp.text or ""
            parts = [
                t.Part.from_function_response(
                    name=c.name, response={"result": registry.call(c.name, dict(c.args or {}))}
                )
                for c in calls
            ]
            self.history.append(t.Content(role="user", parts=parts))
        return None  # tool-turn cap hit
