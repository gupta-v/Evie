import subprocess

from evie.core import registry


def test_copy_sends_utf16_with_bom_via_argv(monkeypatch):
    seen = {}
    monkeypatch.setattr(subprocess, "run", lambda cmd, **k: seen.update(cmd=cmd, **k))
    out = registry.call("copy_to_clipboard", {"text": "hi ☔"})
    assert out == "copied to clipboard"
    assert seen["cmd"] == ["clip"]
    assert seen["input"] == b"\xff\xfe" + "hi ☔".encode("utf-16-le")


def test_copy_failure_is_speakable(monkeypatch):
    def boom(*a, **k):
        raise OSError
    monkeypatch.setattr(subprocess, "run", boom)
    assert "clipboard" in registry.call("copy_to_clipboard", {"text": "x"})
