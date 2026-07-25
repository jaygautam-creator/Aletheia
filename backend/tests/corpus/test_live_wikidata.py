"""Tests for the live Wikidata second source (ADR-0013), offline via a fake transport.

``httpx.MockTransport`` stands in for the real network, so these tests exercise the actual
``wbsearchentities`` request/response parsing without a live call.
"""

from __future__ import annotations

import httpx
import pytest

from aletheia.corpus.live_wikidata import live_wikidata_search
from aletheia.corpus.models import TrustTier


def _handler(search_hits: list[dict[str, str]]) -> httpx.MockTransport:
    def handle(request: httpx.Request) -> httpx.Response:
        assert dict(request.url.params).get("action") == "wbsearchentities"
        return httpx.Response(200, json={"search": search_hits})

    return httpx.MockTransport(handle)


async def test_returns_the_top_entity_as_live_fallback_evidence() -> None:
    transport = _handler(
        search_hits=[
            {
                "id": "Q1234",
                "label": "University of Illinois at Chicago",
                "description": "public research university in Chicago",
            }
        ]
    )
    async with httpx.AsyncClient(transport=transport) as client:
        results = await live_wikidata_search("University of Illinois at Chicago", client=client)

    assert len(results) == 1
    result = results[0]
    assert result.trust_tier is TrustTier.LIVE_FALLBACK
    assert result.connector == "wikidata_live"
    assert result.external_id == "Q1234"
    assert result.url == "https://www.wikidata.org/wiki/Q1234"
    # Label + description rendered as one quotable sentence.
    assert result.text == (
        "University of Illinois at Chicago is public research university in Chicago."
    )
    # A live second source is never corpus-grade and not yet corroborated on its own.
    assert result.corroborated is False


async def test_no_search_hits_returns_empty() -> None:
    async with httpx.AsyncClient(transport=_handler([])) as client:
        results = await live_wikidata_search("asdkjfhaslkdjfhalskdjfh", client=client)

    assert results == []


async def test_entity_without_a_description_returns_empty() -> None:
    # A bare label is not quotable evidence — the second source stays silent rather than
    # offer an empty span the Verifier could never ground against.
    transport = _handler([{"id": "Q9", "label": "Some entity", "description": ""}])
    async with httpx.AsyncClient(transport=transport) as client:
        results = await live_wikidata_search("some entity", client=client)

    assert results == []


async def test_a_long_description_is_truncated_to_the_length_cap() -> None:
    transport = _handler([{"id": "Q1", "label": "X", "description": "word " * 2000}])
    async with httpx.AsyncClient(transport=transport) as client:
        results = await live_wikidata_search("x", client=client)

    assert len(results[0].text) <= 4000


async def test_http_error_propagates_rather_than_being_swallowed() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await live_wikidata_search("anything", client=client)
