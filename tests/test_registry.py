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

    @registry.tool("_t_write", "test", {}, risk="write")
    def _w():
        ran.append(1)
        return "done"

    assert registry.call("_t_write", {}) == registry.NEEDS_APPROVAL
    assert ran == []
    assert registry.call("_t_write", {}, approved=True) == "done"


def test_bad_risk_rejected():
    with pytest.raises(ValueError):
        registry.tool("_t_bad", "x", {}, risk="admin")
