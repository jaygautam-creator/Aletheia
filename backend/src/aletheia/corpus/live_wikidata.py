"""Live Wikidata lookup — the independent second source for corroboration (ADR-0013).

The live Wikipedia path (ADR-0012) is a single source: one page, one opinion. This is its
accountable second opinion. Wikidata shares Wikipedia's umbrella organisation but is a
genuinely different service — hand-curated *structured* statements (an entity's label,
description, and property/value claims) rather than prose — so when it independently
carries the same discrete fact (a date, a nationality, "is a public university"), that is
real corroboration, not the same source read twice.

Like :mod:`live_wikipedia`, this is never ingested, frozen, or benchmarked: a live,
on-demand fetch per query. Every result carries :attr:`TrustTier.LIVE_FALLBACK` — Wikidata
is not corpus-grade, and agreement between it and Wikipedia is expressed by the
``corroborated`` flag on the evidence, never by silently upgrading the tier (ADR-0003).
"""

from __future__ import annotations

import httpx

from aletheia.corpus.models import TrustTier
from aletheia.corpus.retrieval import RetrievedEvidence

WIKIDATA_API = "https://www.wikidata.org/w/api.php"
#: Same polite, honest identification the Wikipedia path uses — not a scrape.
_USER_AGENT = "Aletheia/0.1 (https://github.com/jaygautam-creator/Aletheia; research tool)"
_TIMEOUT = 10.0

#: Wikidata's descriptions are short by design; this bounds the synthesised evidence text
#: the same way :mod:`live_wikipedia` bounds a raw extract, against a request-size failure.
_MAX_EVIDENCE_CHARS = 4000


async def _search_entity(client: httpx.AsyncClient, query: str) -> dict[str, str] | None:
    """The best-matching Wikidata entity for ``query`` as ``{id, label, description}``.

    Returns ``None`` when nothing matches. ``wbsearchentities`` already carries the label
    and (usually) a description, so a single call is enough for a first-pass second source;
    a richer statement fetch can layer on later without changing this contract.
    """
    response = await client.get(
        WIKIDATA_API,
        params={
            "action": "wbsearchentities",
            "search": query,
            "language": "en",
            "uselang": "en",
            "format": "json",
            "limit": 1,
        },
    )
    response.raise_for_status()
    hits = response.json().get("search", [])
    if not hits:
        return None
    hit = hits[0]
    return {
        "id": str(hit.get("id") or ""),
        "label": str(hit.get("label") or ""),
        "description": str(hit.get("description") or ""),
    }


def _evidence_text(label: str, description: str) -> str:
    """Render an entity's label and description as one quotable sentence.

    The Verifier grounds by quoting a verbatim span, so the second source has to offer
    *text*, not a raw triple. "<label> is <description>." is the honest minimal rendering
    of a Wikidata entry; empty when there is nothing quotable to say.
    """
    label = label.strip()
    description = description.strip()
    if not label or not description:
        return ""
    return f"{label} is {description}."[:_MAX_EVIDENCE_CHARS]


async def _search_and_describe(client: httpx.AsyncClient, query: str) -> list[RetrievedEvidence]:
    """The shared lookup, once a client (owned or injected) is available."""
    entity = await _search_entity(client, query)
    if entity is None:
        return []
    text = _evidence_text(entity["label"], entity["description"])
    if not text.strip():
        return []

    entity_id = entity["id"]
    url = f"https://www.wikidata.org/wiki/{entity_id}" if entity_id else None
    return [
        RetrievedEvidence(
            chunk_id=0,
            source_id=0,
            connector="wikidata_live",
            external_id=entity_id or entity["label"],
            title=entity["label"],
            url=url,
            trust_tier=TrustTier.LIVE_FALLBACK,
            kind="entity",
            text=text.strip(),
            score=1.0,
        )
    ]


async def live_wikidata_search(
    query: str, *, client: httpx.AsyncClient | None = None
) -> list[RetrievedEvidence]:
    """Look Wikidata up live and return its top entity as one lower-trust evidence item.

    Returns an empty list (not an error) when nothing matches or the entity has no
    quotable description, so a missing second source degrades cleanly to "uncorroborated"
    rather than failing the query. ``client`` is injectable so tests exercise the parsing
    against a fake transport; ``None`` (production default) opens a short-lived client.
    """
    if client is not None:
        return await _search_and_describe(client, query)
    async with httpx.AsyncClient(timeout=_TIMEOUT, headers={"User-Agent": _USER_AGENT}) as owned:
        return await _search_and_describe(owned, query)
