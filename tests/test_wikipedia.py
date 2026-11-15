import pytest

import evie.tools  # noqa: F401
from evie.core import registry
from evie.services import wikipedia as wiki
from evie.services.text import shorten


class FakeWrapper:
    def __init__(self, out=None, boom=None):
        self.out, self.boom, self.asked = out, boom, []

    def run(self, q):
        self.asked.append(q)
        if self.boom:
            raise self.boom
        return self.out


KUBE = "Page: Kubernetes\nSummary: Kubernetes (), also known as K8s, is an open-source container orchestration system. Originally designed by Google, the project is now maintained by the CNCF. It works with many tools."


def test_summary_drops_the_page_prefix_and_empty_parentheses():
    w = FakeWrapper(KUBE)
    out = wiki.summary("kubernetes", wrapper=w)
    assert out.startswith("Kubernetes: Kubernetes, also known as K8s, is an open-source")
    assert "()" not in out and "Page:" not in out and "Summary:" not in out
    assert w.asked == ["kubernetes"]


def test_summary_is_cut_at_a_sentence_end_for_speech():
    long = "Page: X\nSummary: " + "First sentence here. " * 40
    out = wiki.summary("x", wrapper=FakeWrapper(long))
    assert len(out) <= 400 and out.endswith("here.")


def test_a_miss_and_a_failure_are_spoken():
    with pytest.raises(wiki.WikipediaError, match="couldn't find a Wikipedia article for zzz"):
        wiki.summary("zzz", wrapper=FakeWrapper("No good Wikipedia Search Result was found"))
    with pytest.raises(wiki.WikipediaError, match="couldn't reach Wikipedia"):
        wiki.summary("x", wrapper=FakeWrapper(boom=OSError("offline")))


def test_non_ascii_survives():
    out = wiki.summary("kalam", wrapper=FakeWrapper("Page: A. P. J. Abdul Kalam\nSummary: Born in Rameswaram ə India."))
    assert "ə" in out


def test_tool_uses_the_service_and_speaks_errors(monkeypatch):
    monkeypatch.setattr(wiki, "_wrapper", lambda: FakeWrapper(KUBE))
    assert registry.call("wikipedia", {"topic": "kubernetes"}).startswith("Kubernetes: ")
    monkeypatch.setattr(wiki, "_wrapper", lambda: FakeWrapper("No good Wikipedia Search Result was found"))
    assert "couldn't find a Wikipedia article" in registry.call("wikipedia", {"topic": "zzzz"})


def test_shorten():
    assert shorten("short", 50) == "short"
    assert shorten("One. Two. Three. Four.", 15) == "One. Two."  # sentence boundary
    assert shorten("a" * 5 + " " + "b" * 30, 20).endswith("...")  # no sentence: word cut
