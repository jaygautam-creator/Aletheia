"""Tests for the live Wikipedia fallback (ADR-0012), offline via a fake HTTP transport.

``httpx.MockTransport`` stands in for the real network, so these tests exercise the
actual request/response parsing without a live call.
"""

from __future__ import annotations

import httpx
import pytest

from aletheia.corpus.live_wikipedia import live_wikipedia_search
from aletheia.corpus.models import TrustTier


def _handler(search_hits: list[dict[str, str]], extract: str | None) -> httpx.MockTransport:
    def handle(request: httpx.Request) -> httpx.Response:
        params = dict(request.url.params)
        if params.get("list") == "search":
            return httpx.Response(200, json={"query": {"search": search_hits}})
        # prop=extracts
        title = params["titles"]
        pages = {"1": {"title": title, "extract": extract}} if extract is not None else {}
        return httpx.Response(200, json={"query": {"pages": pages}})

    return httpx.MockTransport(handle)


async def test_returns_the_top_hit_as_live_fallback_evidence() -> None:
    transport = _handler(
        search_hits=[{"title": "1990 FIFA World Cup"}],
        extract="West Germany won the 1990 FIFA World Cup, defeating Argentina 1-0.",
    )
    async with httpx.AsyncClient(transport=transport) as client:
        results = await live_wikipedia_search("who won the 1990 world cup?", client=client)

    assert len(results) == 1
    result = results[0]
    assert result.trust_tier is TrustTier.LIVE_FALLBACK
    assert result.connector == "wikipedia_live"
    assert result.title == "1990 FIFA World Cup"
    assert result.url == "https://en.wikipedia.org/wiki/1990_FIFA_World_Cup"
    assert "West Germany won" in result.text


async def test_no_search_hits_returns_empty() -> None:
    transport = _handler(search_hits=[], extract=None)
    async with httpx.AsyncClient(transport=transport) as client:
        results = await live_wikipedia_search("asdkjfhaslkdjfhalskdjfh", client=client)

    assert results == []


async def test_a_page_with_no_extract_returns_empty() -> None:
    transport = _handler(search_hits=[{"title": "A stub page"}], extract="")
    async with httpx.AsyncClient(transport=transport) as client:
        results = await live_wikipedia_search("a stub page", client=client)

    assert results == []


async def test_page_title_with_spaces_becomes_underscored_in_the_url() -> None:
    transport = _handler(
        search_hits=[{"title": "Marie Curie"}], extract="Marie Curie was a physicist and chemist."
    )
    async with httpx.AsyncClient(transport=transport) as client:
        results = await live_wikipedia_search("marie curie", client=client)

    assert results[0].url == "https://en.wikipedia.org/wiki/Marie_Curie"


async def test_a_long_extract_is_truncated_to_the_length_cap() -> None:
    # Regression test: a real Wikipedia biography/country article can run far longer
    # than a corpus chunk, and an untruncated extract blew Groq's request-size limit
    # during manual testing (2026-07-19). The cap must actually bound the text handed
    # to the LLM, not just the intro-only API param.
    huge_extract = "word " * 2000  # 10,000 chars, well over the cap
    transport = _handler(search_hits=[{"title": "A very long article"}], extract=huge_extract)
    async with httpx.AsyncClient(transport=transport) as client:
        results = await live_wikipedia_search("a very long article", client=client)

    assert len(results[0].text) <= 4000


async def test_http_error_propagates_rather_than_being_swallowed() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await live_wikipedia_search("anything", client=client)
