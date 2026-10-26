import asyncio
import logging

from ddgs import DDGS

logger = logging.getLogger(__name__)

_MAX_RESULTS = 4
_MAX_SNIPPET_CHARS = 500


class SearchResult:
    def __init__(self, title: str, url: str, snippet: str) -> None:
        self.title = title
        self.url = url
        self.snippet = snippet


def _search_sync(query: str) -> list[dict]:
    return DDGS().text(query[:400], max_results=_MAX_RESULTS)


async def search_web(query: str) -> list[SearchResult]:
    """DuckDuckGo search via the free `ddgs` library — no API key, no
    account, no quota. Unlike a dedicated search API this scrapes public
    search results rather than calling an official endpoint, so it can be
    rate-limited or change behavior without notice; any failure degrades to
    no results rather than breaking the conversation turn. `ddgs` is a
    blocking/sync library, so it runs off the event loop via to_thread.
    """
    if not query:
        return []

    try:
        raw_results = await asyncio.to_thread(_search_sync, query)
    except Exception:
        logger.exception("Web search failed for query %r; proceeding without results", query)
        return []

    results = []
    for item in raw_results[:_MAX_RESULTS]:
        title = str(item.get("title") or "").strip()
        url = str(item.get("href") or "").strip()
        snippet = str(item.get("body") or "").strip()[:_MAX_SNIPPET_CHARS]
        if title and url:
            results.append(SearchResult(title=title, url=url, snippet=snippet))
    return results


def format_search_results(results: list[SearchResult]) -> str:
    if not results:
        return "No search results found."
    lines = [f"- {r.title} ({r.url}): {r.snippet}" for r in results]
    return "\n".join(lines)
