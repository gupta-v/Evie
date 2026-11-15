import pytest

import evie.tools  # noqa: F401
from evie.core import registry


def test_get_time_registered_and_callable():
    assert any(s["name"] == "get_time" for s in registry.specs())
    assert registry.call("get_time", {})


def test_unknown_tool_returns_error_not_raise():
    assert registry.call("nope", {}).startswith("error")


def test_metadata_defaults_to_read_not_fast():
    m = registry.meta("get_time")
    assert (m.risk, m.fast) == ("read", False)


def test_write_tool_blocked_until_approved():
    ran = []

    @registry.tool(risk="write", name="_t_write")
    def _w():
        """Test write tool."""
        ran.append(1)
        return "done"

    assert registry.call("_t_write", {}) == registry.NEEDS_APPROVAL
    assert ran == []
    assert registry.call("_t_write", {}, approved=True) == "done"


def test_bad_risk_rejected():
    with pytest.raises(ValueError):
        registry.tool(risk="admin")


def _spec(name):
    return next(s for s in registry.specs() if s["name"] == name)


def test_schema_comes_from_type_hints_and_docstring():
    @registry.tool(name="_t_schema")
    def _s(a: int, b: str, c: float = 1.0, d: bool = False):
        """Line one.
        Line two.

        Args:
            a: the a
            b: the b
            c: the c
            d: the d
        """
        return ""

    spec = _spec("_t_schema")
    assert spec["description"] == "Line one. Line two."
    assert spec["input_schema"]["required"] == ["a", "b"]
    props = spec["input_schema"]["properties"]
    assert props["a"] == {"type": "integer", "description": "the a"}
    assert props["b"] == {"type": "string", "description": "the b"}
    assert props["c"]["type"] == "number" and props["d"]["type"] == "boolean"
    assert "title" not in str(spec["input_schema"])


def test_tool_without_docstring_rejected():
    with pytest.raises(ValueError, match="docstring"):
        @registry.tool(name="_t_nodoc")
        def _n():
            return ""


def test_params_must_be_documented_in_args_section():
    with pytest.raises(ValueError, match="Google-Style"):
        @registry.tool(name="_t_undoc")
        def _u(x: int):
            """Has a param but no Args section."""
            return ""


def test_model_output_is_coerced_and_extra_args_ignored():
    @registry.tool(name="_t_coerce")
    def _c(n: int):
        """Echo n plus one.

        Args:
            n: the number
        """
        return n + 1

    assert registry.call("_t_coerce", {"n": "5", "junk": 1}) == "6"  # "5" -> 5, junk ignored


def test_invalid_arguments_return_retryable_message_and_do_not_run():
    from typing import Annotated

    from pydantic import Field

    ran = []

    @registry.tool(name="_t_range")
    def _r(n: Annotated[int, Field(ge=0, le=10)]):
        """Range check.

        Args:
            n: a number from 0 to 10
        """
        ran.append(n)
        return "ok"

    out = registry.call("_t_range", {"n": 99})
    assert out.startswith("error: invalid arguments") and "n:" in out
    assert ran == []
    assert registry.call("_t_range", {}).startswith("error: invalid arguments")  # missing required


def test_wrapped_tool_keeps_signature_schema():
    # music tools are wrapped by _speakable; schema must still come from the real signature
    spec = _spec("music_set_volume")
    level = spec["input_schema"]["properties"]["level"]
    assert level["type"] == "integer" and (level["minimum"], level["maximum"]) == (0, 100)
    assert level["description"] == "Target volume, 0-100."
    assert spec["input_schema"]["required"] == ["level"]
