"""Live web fallback — the tier-2 second source, tried only when Wikidata is empty (ADR-0013).

Wikidata is the accountable first choice for a second opinion, but it only covers entities it
holds structured statements about. When it has nothing, this broadens coverage via
DuckDuckGo's Instant Answer API (free, no auth, no scrape) — at the cost of accountability,
which is why it is a fallback and never the primary corroborator.

Two guards keep "trustable" honest:

- **Allowlist.** Only an abstract whose source URL is on a small, explicit list of
  accountable domains (``.gov`` and a few established reference works) is accepted; an
  arbitrary web page is not evidence.
- **Independence.** DuckDuckGo's abstract is frequently *sourced from Wikipedia itself*, so
  a Wikipedia/Wikidata-hosted answer is rejected here — otherwise it would fake independent
  agreement with the primary Wikipedia source and wrongly trip corroboration (ADR-0013).

Every result stays :attr:`TrustTier.LIVE_FALLBACK`.
"""

from __future__ import annotations

import httpx

from aletheia.corpus.models import TrustTier
from aletheia.corpus.retrieval import RetrievedEvidence

DUCKDUCKGO_API = "https://api.duckduckgo.com/"
_USER_AGENT = "Aletheia/0.1 (https://github.com/jaygautam-creator/Aletheia; research tool)"
_TIMEOUT = 10.0
_MAX_EVIDENCE_CHARS = 4000

#: Accountable domains this fallback will quote from. Deliberately narrow (ADR-0013 says
#: start narrow and widen only with justification). Matched as host suffixes.
_ALLOWED_HOST_SUFFIXES = (".gov", "britannica.com", "nih.gov", "who.int")

#: Never accepted here: the primary pair's own hosts. An answer DuckDuckGo drew from
#: Wikipedia is not independent of the Wikipedia source, so it must not count toward
#: corroboration.
_EXCLUDED_HOST_SUFFIXES = ("wikipedia.org", "wikidata.org")


def _host_is_allowed(url: str) -> bool:
    """Whether ``url``'s host is an accountable, independent source (see the suffix lists)."""
    host = httpx.URL(url).host.lower()
    if not host or any(host.endswith(suffix) for suffix in _EXCLUDED_HOST_SUFFIXES):
        return False
    return any(
        host == suffix.lstrip(".") or host.endswith(suffix) for suffix in _ALLOWED_HOST_SUFFIXES
    )


async def _instant_answer(client: httpx.AsyncClient, query: str) -> list[RetrievedEvidence]:
    response = await client.get(
        DUCKDUCKGO_API,
        params={"q": query, "format": "json", "no_html": 1, "t": "aletheia"},
    )
    response.raise_for_status()
    payload = response.json()
    abstract = str(payload.get("AbstractText") or "").strip()
    url = str(payload.get("AbstractURL") or "").strip()
    if not abstract or not url or not _host_is_allowed(url):
        return []

    heading = str(payload.get("Heading") or url).strip()
    return [
        RetrievedEvidence(
            chunk_id=0,
            source_id=0,
            connector="web_live",
            external_id=url,
            title=heading,
            url=url,
            trust_tier=TrustTier.LIVE_FALLBACK,
            kind="abstract",
            text=abstract[:_MAX_EVIDENCE_CHARS],
            score=1.0,
        )
    ]


async def live_web_search(
    query: str, *, client: httpx.AsyncClient | None = None
) -> list[RetrievedEvidence]:
    """Look up a DuckDuckGo instant answer, returning it only from an accountable, independent host.

    Returns an empty list (not an error) when there is no instant answer, no source URL, or
    the source is off-allowlist or one of the excluded primary hosts — so an unusable
    fallback degrades cleanly to "uncorroborated". ``client`` is injectable for tests.
    """
    if client is not None:
        return await _instant_answer(client, query)
    async with httpx.AsyncClient(timeout=_TIMEOUT, headers={"User-Agent": _USER_AGENT}) as owned:
        return await _instant_answer(owned, query)
