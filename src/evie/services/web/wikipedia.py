"""Wikipedia lookups for stable facts: people, places, definitions. Uses LangChain's
WikipediaAPIWrapper (the `wikipedia` package underneath), cleaned into a couple of spoken sentences.

Measured: ~2 s for a hit, ~0.7 s for a miss.

shortcut: langchain-community announced it is being sunset; the wrapper only calls the `wikipedia`
package, so if it is ever removed use that package directly and delete the import below.
"""
import re
import warnings

from evie.utils.text import shorten

_MAX_CHARS = 380
_EMPTY_PARENS = re.compile(r"\s*\(\s*[,;]?\s*\)")  # left where Wikipedia dropped a pronunciation
_MISS = "No good Wikipedia Search Result was found"


class WikipediaError(Exception):
    """Message is safe to read aloud."""


def _wrapper():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # the sunset DeprecationWarning is noise here
        from langchain_community.utilities import WikipediaAPIWrapper

    return WikipediaAPIWrapper(top_k_results=1, doc_content_chars_max=700)


def summary(topic: str, wrapper=None) -> str:
    """'Title: first sentences...' for the best matching article. Raises WikipediaError on a miss."""
    try:
        raw = (wrapper or _wrapper()).run(topic)
    except Exception as e:
        raise WikipediaError("I couldn't reach Wikipedia right now.") from e
    if not raw or _MISS in raw:
        raise WikipediaError(f"I couldn't find a Wikipedia article for {topic}.")
    page = raw.split("\n\n")[0]  # top_k is 1, but be safe
    title, _, body = page.partition("\nSummary:")
    title = title.removeprefix("Page:").strip()
    body = _EMPTY_PARENS.sub("", " ".join(body.split()))
    return f"{title}: {shorten(body, _MAX_CHARS)}" if body else title
