"""ToolRegistry: one list of tools for the agent, native or MCP-backed alike.

Each tool declares `risk` ("read" or "write") and `fast` (eligible for the fast router).
The approval gate and router read this metadata, so adding a tool never touches the brain.
"""
from dataclasses import dataclass
from typing import Callable

NEEDS_APPROVAL = "needs approval: this action changes something. Ask the user to confirm."


@dataclass(frozen=True)
class Meta:
    risk: str = "read"
    fast: bool = False


_TOOLS: dict[str, dict] = {}


def tool(name: str, description: str, schema: dict, *, risk: str = "read", fast: bool = False):
    """Register a native function. `schema` is the JSON-schema `properties` dict."""
    if risk not in ("read", "write"):
        raise ValueError(f"risk must be 'read' or 'write', got {risk!r}")

    def deco(fn: Callable[..., str]):
        _TOOLS[name] = {
            "fn": fn,
            "meta": Meta(risk, fast),
            "spec": {
                "name": name,
                "description": description,
                "input_schema": {"type": "object", "properties": schema, "required": list(schema)},
            },
        }
        return fn

    return deco


def specs() -> list[dict]:
    return [t["spec"] for t in _TOOLS.values()]


def meta(name: str) -> Meta | None:
    return _TOOLS[name]["meta"] if name in _TOOLS else None


def call(name: str, args: dict, *, approved: bool = False) -> str:
    if name not in _TOOLS:
        return f"error: unknown tool {name}"
    if _TOOLS[name]["meta"].risk == "write" and not approved:
        return NEEDS_APPROVAL
    try:
        return str(_TOOLS[name]["fn"](**args))
    except Exception as e:  # tool errors go back to the model, not crash the loop
        return f"error: {e}"
