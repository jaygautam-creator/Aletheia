"""Live Wikipedia fallback — the lower-trust tier ADR-0003 deferred, now built (ADR-0012).

Unlike every other evidence source in this project, this one is never ingested,
frozen, or benchmarked: it is a live, on-demand fetch per query, used only when the
Intake guard classifies a query as general (non-medical) rather than in-scope for the
curated corpus. Two calls to Wikipedia's own REST API (no auth, no scraping, one
accountable source): search for the best-matching page title, then fetch its plain-text
extract. Every result carries :attr:`TrustTier.LIVE_FALLBACK`, never
``CURATED_CORPUS`` — this must never be silently mixed in as though it were
corpus-grade (ADR-0003).
"""

from __future__ import annotations

import httpx

from aletheia.corpus.models import TrustTier
from aletheia.corpus.retrieval import RetrievedEvidence

WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
#: Wikipedia asks anonymous API clients to identify themselves; this is not a scrape,
#: just a polite, honest User-Agent for the project's own live-fallback calls.
_USER_AGENT = "Aletheia/0.1 (https://github.com/jaygautam-creator/Aletheia; research tool)"
_TIMEOUT = 10.0


async def _search_title(client: httpx.AsyncClient, query: str) -> str | None:
    """The best-matching page title for ``query``, or ``None`` if nothing matches."""
    response = await client.get(
        WIKIPEDIA_API,
        params={
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": 1,
            "format": "json",
        },
    )
    response.raise_for_status()
    hits = response.json().get("query", {}).get("search", [])
    return str(hits[0]["title"]) if hits else None


async def _fetch_extract(client: httpx.AsyncClient, title: str) -> str:
    """The plain-text summary (intro extract) of the Wikipedia page titled ``title``."""
    response = await client.get(
        WIKIPEDIA_API,
        params={
            "action": "query",
            "prop": "extracts",
            "explaintext": 1,
            "titles": title,
            "format": "json",
        },
    )
    response.raise_for_status()
    pages = response.json().get("query", {}).get("pages", {})
    for page in pages.values():
        return str(page.get("extract") or "")
    return ""


async def _search_and_extract(client: httpx.AsyncClient, query: str) -> list[RetrievedEvidence]:
    """The shared lookup, once a client (owned or injected) is available."""
    title = await _search_title(client, query)
    if title is None:
        return []
    extract = await _fetch_extract(client, title)
    if not extract.strip():
        return []

    url = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
    return [
        RetrievedEvidence(
            chunk_id=0,
            source_id=0,
            connector="wikipedia_live",
            external_id=title,
            title=title,
            url=url,
            trust_tier=TrustTier.LIVE_FALLBACK,
            kind="extract",
            text=extract.strip(),
            score=1.0,
        )
    ]


async def live_wikipedia_search(
    query: str, *, client: httpx.AsyncClient | None = None
) -> list[RetrievedEvidence]:
    """Search Wikipedia live and return its top hit as a single lower-trust evidence item.

    Returns an empty list (not an error) when nothing matches or the page has no
    extract, so the caller degrades to ``Unverifiable`` exactly like an empty corpus
    search does — no fabricated evidence, no special-cased failure path. ``client`` is
    injectable so tests can exercise the parsing logic against a fake transport rather
    than the real network; ``None`` (the production default) opens a short-lived client
    per call.
    """
    if client is not None:
        return await _search_and_extract(client, query)
    async with httpx.AsyncClient(timeout=_TIMEOUT, headers={"User-Agent": _USER_AGENT}) as owned:
        return await _search_and_extract(owned, query)
