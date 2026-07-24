"""Tests for the live multi-source orchestrator (ADR-0013), offline via a fake transport.

One ``httpx.MockTransport`` routes by host so the same injected client serves both the
Wikipedia and the Wikidata fetch, exercising the real parallel-gather path.
"""

from __future__ import annotations

import httpx

from aletheia.corpus.live_search import live_multi_source_search


def _route(
    *,
    wiki_hits: list[dict[str, str]],
    extract: str,
    wikidata_hits: list[dict[str, str]],
    web: dict[str, object] | None = None,
    hits: list[str] | None = None,
) -> httpx.MockTransport:
    def handle(request: httpx.Request) -> httpx.Response:
        if hits is not None:
            hits.append(request.url.host)
        if request.url.host == "www.wikidata.org":
            return httpx.Response(200, json={"search": wikidata_hits})
        if request.url.host == "api.duckduckgo.com":
            return httpx.Response(200, json=web or {})
        # en.wikipedia.org: search then extract
        params = dict(request.url.params)
        if params.get("list") == "search":
            return httpx.Response(200, json={"query": {"search": wiki_hits}})
        pages = {"1": {"title": params["titles"], "extract": extract}}
        return httpx.Response(200, json={"query": {"pages": pages}})

    return httpx.MockTransport(handle)


async def test_returns_both_sources_together_in_order() -> None:
    transport = _route(
        wiki_hits=[{"title": "University of Illinois at Chicago"}],
        extract="The University of Illinois at Chicago is a state-funded public university.",
        wikidata_hits=[
            {
                "id": "Q1234",
                "label": "University of Illinois at Chicago",
                "description": "public university in Chicago",
            }
        ],
    )
    async with httpx.AsyncClient(transport=transport) as client:
        results = await live_multi_source_search("UIC state funded", client=client)

    assert [r.connector for r in results] == ["wikipedia_live", "wikidata_live"]
    assert "state-funded" in results[0].text
    assert results[1].external_id == "Q1234"


async def test_one_source_empty_still_returns_the_other() -> None:
    transport = _route(
        wiki_hits=[{"title": "Some Page"}],
        extract="A prose fact about the page.",
        wikidata_hits=[],  # Wikidata has nothing
    )
    async with httpx.AsyncClient(transport=transport) as client:
        results = await live_multi_source_search("some page", client=client)

    assert [r.connector for r in results] == ["wikipedia_live"]


async def test_a_failing_source_does_not_sink_the_other() -> None:
    # Wikidata 503s; Wikipedia still answers. The live path must degrade, not raise.
    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.host == "www.wikidata.org":
            return httpx.Response(503)
        params = dict(request.url.params)
        if params.get("list") == "search":
            return httpx.Response(200, json={"query": {"search": [{"title": "Marie Curie"}]}})
        return httpx.Response(
            200, json={"query": {"pages": {"1": {"extract": "Marie Curie was a physicist."}}}}
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        results = await live_multi_source_search("marie curie", client=client)

    assert [r.connector for r in results] == ["wikipedia_live"]
    assert "physicist" in results[0].text


async def test_both_empty_returns_empty() -> None:
    transport = _route(wiki_hits=[], extract="", wikidata_hits=[])
    async with httpx.AsyncClient(transport=transport) as client:
        results = await live_multi_source_search("nothing matches this", client=client)

    assert results == []


async def test_web_fallback_fills_the_second_slot_when_wikidata_is_empty() -> None:
    transport = _route(
        wiki_hits=[{"title": "CDC"}],
        extract="The CDC is a US public health agency.",
        wikidata_hits=[],  # Wikidata has nothing -> the tiered web fallback takes over
        web={
            "AbstractText": "US federal public health agency.",
            "AbstractURL": "https://www.cdc.gov/",
        },
    )
    async with httpx.AsyncClient(transport=transport) as client:
        results = await live_multi_source_search("what is the CDC", client=client)

    assert [r.connector for r in results] == ["wikipedia_live", "web_live"]


async def test_web_fallback_is_not_consulted_when_wikidata_answers() -> None:
    # Accountable-first: if Wikidata has an answer, the broader web tier is never hit.
    hits: list[str] = []
    transport = _route(
        wiki_hits=[{"title": "Marie Curie"}],
        extract="Marie Curie was a physicist.",
        wikidata_hits=[
            {"id": "Q7186", "label": "Marie Curie", "description": "physicist and chemist"}
        ],
        hits=hits,
    )
    async with httpx.AsyncClient(transport=transport) as client:
        results = await live_multi_source_search("marie curie", client=client)

    assert [r.connector for r in results] == ["wikipedia_live", "wikidata_live"]
    assert "api.duckduckgo.com" not in hits
