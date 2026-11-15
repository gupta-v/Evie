"""Answering questions from the web (not opening a browser: that is open_website)."""
from typing import Annotated

from pydantic import Field

from evie.core.registry import tool
from evie.services.web import websearch, wikipedia as wiki


@tool
def web_search(query: Annotated[str, Field(min_length=2)]) -> str:
    """Search the web and read the results to answer the user's question. Use this for anything that
    needs current or outside information: courses, news, prices, facts, how-tos. Answer in one or two
    spoken sentences from the results, naming a site only when it helps. Do not open a browser unless
    the user asks to see the page.

    Args:
        query: What to search for, as a short search phrase.
    """
    try:
        res = websearch.search(query)
    except websearch.SearchError as e:
        return str(e)
    if not res.hits and not res.answer:
        return f"No results found for '{query}'."
    lines = [f"Answer: {res.answer}"] if res.answer else []
    lines += [f"{i}. {h.title} ({h.site}): {h.snippet}" for i, h in enumerate(res.hits, 1)]
    return "\n".join(lines)


@tool
def wikipedia(topic: Annotated[str, Field(min_length=2)]) -> str:
    """Look up a person, place, concept or thing on Wikipedia and answer from the summary. Use this
    for stable facts and definitions (who is, what is, where is). For news, prices, products or
    anything recent use web_search instead. Answer in one or two spoken sentences.

    Args:
        topic: The name of the person, place or thing to look up.
    """
    try:
        return wiki.summary(topic)
    except wiki.WikipediaError as e:
        return str(e)
