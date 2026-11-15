"""ToolRegistry: one list of tools for the agent, native or MCP-backed alike.

Tools are LangChain `StructuredTool`s built with langchain's `@tool` machinery: name from the
function, description and per-argument text from the Google-style docstring, schema and argument
validation (pydantic) from the type hints:

    @tool(fast=True)
    def music_set_volume(level: Annotated[int, Field(ge=0, le=100)]) -> str:
        \"\"\"Set music volume, rounded to steps of 5.

        Args:
            level: Target volume, 0-100.
        \"\"\"

LangChain has no notion of risk or speed, so our `tool` adds two flags, kept in `Meta` and also
copied to `tool.metadata`: `risk` ("read" or "write") and `fast` (eligible for the fast router).
The approval gate and router read them, so adding a tool never touches the brain.
"""
import sys
from dataclasses import dataclass
from typing import Callable

from langchain_core.tools import BaseTool
from langchain_core.tools import tool as lc_tool
from langchain_core.utils.function_calling import convert_to_openai_function
from pydantic import ValidationError

from evie import config

NEEDS_APPROVAL = (
    "needs approval: this action changes something. Tell the user exactly what you are about to do "
    "and ask them to confirm. Do not retry until they answer."
)
_blocked: tuple[str, dict] | None = None


@dataclass(frozen=True)
class Meta:
    risk: str = "read"
    fast: bool = False


_TOOLS: dict[str, dict] = {}


def _spec(t: BaseTool) -> dict:
    fn = convert_to_openai_function(t)
    params = fn.get("parameters") or {"type": "object", "properties": {}}
    params.setdefault("required", [])
    return {"name": fn["name"], "description": " ".join(fn["description"].split()), "input_schema": params}


def _problems(e: ValidationError) -> str:
    return "; ".join(f"{'.'.join(map(str, x['loc'])) or 'arguments'}: {x['msg']}" for x in e.errors())


def tool(fn: Callable | None = None, *, name: str | None = None, risk: str = "read", fast: bool = False):
    """Register a function as a tool. Use bare `@tool` or `@tool(fast=True, risk="write")`.
    Returns the LangChain tool object."""
    if risk not in ("read", "write"):
        raise ValueError(f"risk must be 'read' or 'write', got {risk!r}")

    def register(f: Callable[..., str]) -> BaseTool:
        t = lc_tool(name, f, parse_docstring=True) if name else lc_tool(f, parse_docstring=True)
        t.metadata = {"risk": risk, "fast": fast}
        _TOOLS[t.name] = {"tool": t, "meta": Meta(risk, fast), "spec": _spec(t)}
        return t

    return register(fn) if fn is not None else register


def take_blocked() -> tuple[str, dict] | None:
    """The write call that was just blocked awaiting approval, if any (cleared on read)."""
    global _blocked
    b, _blocked = _blocked, None
    return b


def specs() -> list[dict]:
    return [t["spec"] for t in _TOOLS.values()]


def meta(name: str) -> Meta | None:
    return _TOOLS[name]["meta"] if name in _TOOLS else None


def call(name: str, args: dict, *, approved: bool = False) -> str:
    out = _call(name, args, approved)
    if config.DEBUG:
        print(f"[tool] {name}({args}) -> {out}", file=sys.stderr)
    return out


def _call(name: str, args: dict, approved: bool) -> str:
    if name not in _TOOLS:
        return f"error: unknown tool {name}"
    if _TOOLS[name]["meta"].risk == "write" and not approved:
        global _blocked
        _blocked = (name, args)
        return NEEDS_APPROVAL
    try:
        return str(_TOOLS[name]["tool"].invoke(args))
    except ValidationError as e:
        return f"error: invalid arguments, {_problems(e)}"
    except Exception as e:  # tool errors go back to the model, not crash the loop
        return f"error: {e}"
