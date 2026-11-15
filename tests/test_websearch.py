import pytest

import evie.tools  # noqa: F401
from evie import config
from evie.core import registry
from evie.services.web import websearch

ROWS = [
    {"title": "Microsoft DevOps Certificate", "href": "https://www.bing.com/aclick?ld=abc", "body": "sponsored"},
    {"title": "Best Cloud Courses [2026] | Coursera", "href": "https://www.coursera.org/courses?q=cloud", "body": "Cloud courses can help you learn   scalable systems, managing costs and a lot more words " * 4},
    {"title": "Best DevOps Courses | Coursera", "href": "https://www.coursera.org/courses?q=devops", "body": "second coursera result"},
    {"title": "AWS CloudOps Associate (Udemy)", "href": "https://www.udemy.com/topic/aws", "body": "Learn CloudOps today."},
]


@pytest.fixture(autouse=True)
def no_key(monkeypatch):
    monkeypatch.setattr(config, "TAVILY_API_KEY", None)  # a real key in .env must not make tests go online


def fake(rows):
    return lambda q, n: rows


def test_ads_and_repeat_sites_are_dropped_and_text_is_short():
    res = websearch.search("cloud ops", raw=fake(ROWS))
    assert res.answer is None
    assert [h.site for h in res.hits] == ["coursera.org", "udemy.com"]  # no bing ad, one result per site
    assert res.hits[0].title == "Best Cloud Courses [2026]"  # site name after the bar removed
    assert len(res.hits[0].snippet) <= websearch.SNIPPET_CHARS + 3 and res.hits[0].snippet.endswith("...")
    assert "  " not in res.hits[0].snippet


def test_limit_is_respected():
    many = [{"title": f"T{i}", "href": f"https://site{i}.com/x", "body": "b"} for i in range(10)]
    assert len(websearch.search("q", n=3, raw=fake(many)).hits) == 3


def test_failure_is_spoken_not_raised():
    def boom(q, n):
        raise RuntimeError("rate limited")

    with pytest.raises(websearch.SearchError, match="couldn't reach"):
        websearch.search("q", raw=boom)


def test_tavily_is_used_when_a_key_is_set_and_its_answer_comes_first(monkeypatch):
    monkeypatch.setattr(config, "TAVILY_API_KEY", "tvly-test")
    seen = {}

    def tav(q, n, key):
        seen.update(q=q, key=key)
        return "Coursera and Udemy both list CloudOps courses.", [
            {"title": "AWS CloudOps | Udemy", "href": "https://www.udemy.com/x", "body": "Learn CloudOps."}
        ]

    res = websearch.search("cloud ops", tavily=tav, raw=lambda q, n: pytest.fail("keyless path must not run"))
    assert seen == {"q": "cloud ops", "key": "tvly-test"}
    assert res.answer.startswith("Coursera and Udemy") and [h.site for h in res.hits] == ["udemy.com"]


def test_tavily_request_shape(monkeypatch):
    sent = {}

    class Resp:
        def raise_for_status(self): pass
        def json(self): return {"answer": "A.", "results": [{"title": "T", "url": "https://a.com/x", "content": "c"}]}

    def post(url, **kw):
        sent.update(url=url, **kw)
        return Resp()

    answer, rows = websearch._tavily("q", 5, "tvly-k", post=post)
    assert sent["url"] == "https://api.tavily.com/search" and sent["headers"] == {"Authorization": "Bearer tvly-k"}
    assert sent["json"]["include_answer"] is True and sent["json"]["max_results"] == 5
    assert answer == "A." and rows == [{"title": "T", "href": "https://a.com/x", "body": "c"}]


def test_tool_leads_with_the_answer_then_compact_sources(monkeypatch):
    monkeypatch.setattr(websearch, "search", lambda q: websearch.Result("Try Coursera or Udemy.", [websearch.Hit("T", "udemy.com", "s")]))
    assert registry.call("web_search", {"query": "cloud ops"}).splitlines() == ["Answer: Try Coursera or Udemy.", "1. T (udemy.com): s"]


def test_tool_without_answer_lists_sources_and_handles_empty_and_errors(monkeypatch):
    monkeypatch.setattr(websearch, "_ddgs", fake(ROWS))
    lines = registry.call("web_search", {"query": "cloud ops courses"}).splitlines()
    assert len(lines) == 2 and lines[0].startswith("1. Best Cloud Courses [2026] (coursera.org): ")
    monkeypatch.setattr(websearch, "_ddgs", fake([]))
    assert registry.call("web_search", {"query": "zzzz qqqq"}) == "No results found for 'zzzz qqqq'."

    def boom(q, n):
        raise RuntimeError("x")

    monkeypatch.setattr(websearch, "_ddgs", boom)
    assert "couldn't reach" in registry.call("web_search", {"query": "anything"})
