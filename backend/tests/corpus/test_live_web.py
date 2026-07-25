"""Tests for the allowlisted web fallback (ADR-0013), offline via a fake transport."""

from __future__ import annotations

import httpx
import pytest

from aletheia.corpus.live_web import live_web_search
from aletheia.corpus.models import TrustTier


def _handler(payload: dict[str, object]) -> httpx.MockTransport:
    def handle(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "api.duckduckgo.com"
        return httpx.Response(200, json=payload)

    return httpx.MockTransport(handle)


async def test_accepts_an_answer_from_an_allowlisted_host() -> None:
    transport = _handler(
        {
            "AbstractText": "The CDC is a US federal public health agency.",
            "AbstractURL": "https://www.cdc.gov/about/",
            "Heading": "Centers for Disease Control",
        }
    )
    async with httpx.AsyncClient(transport=transport) as client:
        results = await live_web_search("what is the CDC", client=client)

    assert len(results) == 1
    assert results[0].connector == "web_live"
    assert results[0].trust_tier is TrustTier.LIVE_FALLBACK
    assert "federal public health agency" in results[0].text


async def test_rejects_an_answer_from_an_off_allowlist_host() -> None:
    transport = _handler(
        {"AbstractText": "Some fact.", "AbstractURL": "https://randomblog.example/post"}
    )
    async with httpx.AsyncClient(transport=transport) as client:
        assert await live_web_search("anything", client=client) == []


async def test_rejects_a_wikipedia_sourced_answer_to_preserve_independence() -> None:
    # DuckDuckGo often draws its abstract from Wikipedia; that is not independent of the
    # primary Wikipedia source and must not be allowed to fake corroboration.
    transport = _handler(
        {
            "AbstractText": "Marie Curie was a physicist.",
            "AbstractURL": "https://en.wikipedia.org/wiki/Marie_Curie",
        }
    )
    async with httpx.AsyncClient(transport=transport) as client:
        assert await live_web_search("marie curie", client=client) == []


async def test_empty_abstract_returns_nothing() -> None:
    transport = _handler({"AbstractText": "", "AbstractURL": "https://www.cdc.gov/"})
    async with httpx.AsyncClient(transport=transport) as client:
        assert await live_web_search("nothing", client=client) == []


async def test_http_error_propagates() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await live_web_search("anything", client=client)
