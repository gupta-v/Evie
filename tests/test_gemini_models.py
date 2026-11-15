from types import SimpleNamespace as NS

from evie.providers.gemini import GeminiProvider


class Limited(Exception):
    """Stands in for google's ClientError 429."""


def make(monkeypatch, behaviour):
    """A GeminiProvider whose client is a fake: behaviour[model] is 'limited' or a list of chunks."""
    import google.genai.errors as errors

    class Err(errors.ClientError):
        def __init__(self, code, msg):
            Exception.__init__(self, msg)
            self.code = code

    p = GeminiProvider.__new__(GeminiProvider)
    p.models, p._cool, p.history, p.config = list(behaviour), {}, [], None
    calls = []

    def stream(model, contents, config):
        calls.append(model)
        if behaviour[model] == "limited":
            raise Err(429, "You exceeded your quota. Please retry in 24.4s.")
        return iter(behaviour[model])

    p.client = NS(models=NS(generate_content_stream=stream))
    return p, calls


def test_a_rate_limited_model_is_skipped_and_remembered(monkeypatch):
    p, calls = make(monkeypatch, {"a": "limited", "b": ["chunk1", "chunk2"]})
    assert list(p._chunks()) == ["chunk1", "chunk2"] and calls == ["a", "b"]
    calls.clear()
    list(p._chunks())
    assert calls == ["b"]                     # "a" is cooling down: not asked again


def test_every_model_limited_raises(monkeypatch):
    import pytest

    p, _ = make(monkeypatch, {"a": "limited", "b": "limited"})
    with pytest.raises(Exception):
        list(p._chunks())
