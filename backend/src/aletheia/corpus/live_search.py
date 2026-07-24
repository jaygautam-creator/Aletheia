"""Live multi-source fallback — orchestrates the accountable-first second opinion (ADR-0013).

The single-source live Wikipedia path (ADR-0012) is one page, one opinion. This runs the
independent sources together so the Verifier can ground against more than one, and so a
later corroboration pass can tell when two *distinct* sources carry the same decisive span.

Ordering is "both, tiered" (ADR-0013, decided 2026-07-24): Wikipedia (prose) and Wikidata
(structured, accountable) are fetched in parallel as the primary pair; an allowlisted web
source is a later addition, tried only when the accountable pair comes back empty. Every
result stays :attr:`TrustTier.LIVE_FALLBACK`; agreement is expressed by the ``corroborated``
flag downstream, never by silently upgrading the tier.
"""

from __future__ import annotations

import asyncio

import httpx

from aletheia.corpus.live_wikidata import live_wikidata_search
from aletheia.corpus.live_wikipedia import live_wikipedia_search
from aletheia.corpus.retrieval import RetrievedEvidence

_TIMEOUT = 10.0
_USER_AGENT = "Aletheia/0.1 (https://github.com/jaygautam-creator/Aletheia; research tool)"


async def _gather_sources(client: httpx.AsyncClient, query: str) -> list[RetrievedEvidence]:
    """Fetch the accountable source pair in parallel and concatenate what each returns.

    One source failing must not sink the other, so results are gathered with
    ``return_exceptions`` and a raised source is treated as "returned nothing" — the live
    path already degrades cleanly to ``Unverifiable`` on empty evidence. Order is stable:
    Wikipedia first (prose, broader recall), then Wikidata (the accountable confirmer).
    """
    results = await asyncio.gather(
        live_wikipedia_search(query, client=client),
        live_wikidata_search(query, client=client),
        return_exceptions=True,
    )
    evidence: list[RetrievedEvidence] = []
    for result in results:
        if isinstance(result, BaseException):
            continue
        evidence.extend(result)
    return evidence


async def live_multi_source_search(
    query: str, *, client: httpx.AsyncClient | None = None
) -> list[RetrievedEvidence]:
    """Search every live source and return their evidence together, in source order.

    A drop-in replacement for :func:`live_wikipedia_search` as the pipeline's
    ``general_retrieve``: same signature, same "empty list, not an error" contract, but now
    the Verifier sees an independent second source alongside Wikipedia. ``client`` is
    injectable for tests; ``None`` (production default) opens one short-lived client shared
    by both fetches.
    """
    if client is not None:
        return await _gather_sources(client, query)
    async with httpx.AsyncClient(timeout=_TIMEOUT, headers={"User-Agent": _USER_AGENT}) as owned:
        return await _gather_sources(owned, query)
