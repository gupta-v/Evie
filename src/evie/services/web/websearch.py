"""Web search shaped for a voice assistant: a short answer first, few clean sources, fast.

With TAVILY_API_KEY, one Tavily call returns a ready-made answer plus sources (built for LLM agents,
about a second). Without a key it falls back to keyless DuckDuckGo via `ddgs`, which is slow
(1.7-4.6 s measured) and flaky (returned nothing 2 times in 3 on some engines), so it retries once.
Results are cleaned for speech: ads dropped, one result per site, titles cleaned, snippets short.

shortcut: the Tavily request follows its documented Bearer-header API but was not run against a real
key yet; the fallback is unofficial scraping. Swap in Brave/another API behind `search()` if needed.
"""
import time
from dataclasses import dataclass, field
from urllib.parse import urlparse

from evie import config
from evie.utils.text import clean_title, shorten

SNIPPET_CHARS = 170
_ADS = ("/aclick", "ad_domain=", "ad_provider=", "doubleclick.net", "googleadservices.com")
_TAVILY_URL = "https://api.tavily.com/search"


class SearchError(Exception):
    """Message is safe to read aloud."""


@dataclass(frozen=True)
class Hit:
    title: str
    site: str
    snippet: str


@dataclass(frozen=True)
class Result:
    answer: str | None  # a ready-made summary when the provider gives one
    hits: list[Hit] = field(default_factory=list)


def _tavily(query: str, n: int, key: str, post=None) -> tuple[str | None, list[dict]]:
    import httpx

    r = (post or httpx.post)(
        _TAVILY_URL, headers={"Authorization": f"Bearer {key}"}, timeout=6,
        json={"query": query, "max_results": n, "search_depth": "basic", "include_answer": True},
    )
    r.raise_for_status()
    d = r.json()
    return d.get("answer"), [{"title": x.get("title", ""), "href": x.get("url", ""), "body": x.get("content", "")} for x in d.get("results", [])]


def _ddgs(query: str, n: int) -> list[dict]:
    from ddgs import DDGS  # imported on use: only the keyless fallback needs it

    last = None
    for attempt in range(2):  # it often says "No results" once, then works
        try:
            return DDGS(timeout=6).text(query, max_results=n)
        except Exception as e:
            last = e
            time.sleep(0.4)
    raise last


def search(query: str, n: int = 4, raw=None, tavily=None) -> Result:
    """`raw(query, n) -> rows` and `tavily(query, n, key)` are injectable for tests."""
    try:
        if config.TAVILY_API_KEY:
            answer, rows = (tavily or _tavily)(query, n + 3, config.TAVILY_API_KEY)
        else:
            answer, rows = None, (raw or _ddgs)(query, n + 4)  # extra rows: ads and repeats get dropped
    except Exception as e:
        raise SearchError("I couldn't reach the web search right now.") from e
    hits, seen = [], set()
    for r in rows:
        url = r.get("href", "")
        site = (urlparse(url).hostname or "").removeprefix("www.")
        if not site or any(a in url for a in _ADS) or site in seen:
            continue
        seen.add(site)
        hits.append(Hit(clean_title(r.get("title", "")), site, shorten(r.get("body", ""), SNIPPET_CHARS)))
        if len(hits) == n:
            break
    return Result(shorten(answer, 420) if answer else None, hits)
