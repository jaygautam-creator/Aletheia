"""Offline parsing tests for the PubMed and PMC connectors.

These run entirely against the committed seed fixtures — no network is touched, so they
guard the XML-normalization contract the corpus depends on. Live fetching is exercised
separately (and sparingly) in integration tests.
"""

from __future__ import annotations

from aletheia.corpus.connectors import PmcConnector, PubMedConnector
from aletheia.corpus.seed import SEEDS_DIR

PUBMED_XML = (SEEDS_DIR / "pubmed" / "cardiometabolic.xml").read_text(encoding="utf-8")
PMC_XML = (SEEDS_DIR / "pmc" / "statins.xml").read_text(encoding="utf-8")


def test_pubmed_parses_every_article_in_the_set() -> None:
    sources = PubMedConnector().parse(PUBMED_XML)
    assert [source.external_id for source in sources] == ["40000001", "40000002"]


def test_pubmed_normalizes_title_and_structured_abstract() -> None:
    source = next(s for s in PubMedConnector().parse(PUBMED_XML) if s.external_id == "40000001")

    kinds = [document.kind for document in source.documents]
    assert kinds == ["title", "abstract"]
    assert source.url == "https://pubmed.ncbi.nlm.nih.gov/40000001/"

    abstract = source.documents[1].text
    # Structured-abstract section labels are preserved inline.
    assert abstract.startswith("BACKGROUND:")
    assert "METHODS:" in abstract and "CONCLUSIONS:" in abstract


def test_pubmed_keeps_provenance_metadata() -> None:
    source = next(s for s in PubMedConnector().parse(PUBMED_XML) if s.external_id == "40000001")
    assert source.meta["journal"] == "Journal of Synthetic Cardiology"
    assert source.meta["year"] == "2021"
    assert source.meta["authors"] == ["Okafor", "Lindqvist"]


def test_pmc_normalizes_front_matter_and_body_sections() -> None:
    (source,) = PmcConnector().parse(PMC_XML)

    assert source.external_id == "11000001"
    assert source.url == "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11000001/"
    # Title + abstract + four body sections, in reading order.
    kinds = [document.kind for document in source.documents]
    assert kinds == ["title", "abstract", "body", "body", "body", "body"]
    # The section heading is folded into the body document's text.
    assert source.documents[2].text.startswith("Introduction")


def test_pmc_captures_open_access_license_and_metadata() -> None:
    (source,) = PmcConnector().parse(PMC_XML)
    assert source.license == "open-access"
    assert source.meta["journal"] == "Synthetic Journal of Lipidology"
    assert source.meta["year"] == "2022"
    assert source.meta["authors"] == ["Garcia", "Khan"]
