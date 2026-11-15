import pytest

from evie.core.router import route


@pytest.mark.parametrize("text,want", [
    ("next", ("music_next", {})),
    ("Skip the song, please", ("music_next", {})),
    ("pause", ("music_pause", {})),
    ("hey evie pause the music", ("music_pause", {})),
    ("resume", ("music_play", {})),
    ("volume 40", ("music_set_volume", {"level": 40})),
    ("set the volume to 70 please", ("music_set_volume", {"level": 70})),
    ("louder", ("music_volume_up", {})),
    ("turn it down", ("music_volume_down", {})),
    ("shuffle", ("music_shuffle", {})),
])
def test_fixed_commands_route(text, want):
    assert route(text) == want


@pytest.mark.parametrize("text", [
    "play hola amigo", "next song by arijit singh", "stop the timer", "what's the volume", "volume 500",
    "pause the download of that file", "how do I skip ads", "",
])
def test_everything_else_goes_to_the_llm(text):
    assert route(text) is None


def test_agent_runs_fixed_command_without_the_llm(monkeypatch):
    from evie.core import agent as agent_mod
    from evie.core import registry

    class NoLLM:
        def __init__(self, model): pass
        def respond(self, text): raise AssertionError("LLM must not be called")

    import evie.providers.gemini as g
    monkeypatch.setattr(g, "GeminiProvider", NoLLM)
    monkeypatch.setattr(registry, "call", lambda name, args, approved=False: f"{name}{args}")
    assert agent_mod.Agent().respond("volume 40") == "music_set_volume{'level': 40}"


def test_agent_streams_pieces_in_order_and_remembers_blocked_writes(monkeypatch):
    from evie.core import agent as agent_mod, registry

    class Streaming:
        def __init__(self, model): pass
        def stream(self, text):
            yield "One. "
            yield "Two."

    import evie.providers.gemini as g
    monkeypatch.setattr(g, "GeminiProvider", Streaming)
    assert list(agent_mod.Agent().stream("tell me")) == ["One. ", "Two."]
