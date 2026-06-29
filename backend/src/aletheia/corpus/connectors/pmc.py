"""PMC connector — full open-access article text from a PMCID (JATS XML).

PubMed Central open-access articles ship full text as JATS XML. We normalize the front
matter (title, abstract) plus each top-level body ``<sec>`` into its own document, so
retrieval stays section-aware and a quoted chunk can be traced back to "Methods" or
"Results". The open-access ``<license>`` is captured as provenance — only OA-subset
articles should be ingested, since the curated corpus is meant to be redistributable.
"""

from __future__ import annotations

from typing import Any
from xml.etree import ElementTree as ET

from aletheia.corpus.connectors.base import (
    FetchedSource,
    RawDocument,
    SourceConnector,
    element_text,
    strip_namespaces,
)


class PmcConnector(SourceConnector):
    """Normalizes PMC open-access JATS XML into :class:`FetchedSource` records."""

    name = "pmc"
    db = "pmc"

    def parse(self, raw_xml: str) -> list[FetchedSource]:
        root = strip_namespaces(ET.fromstring(raw_xml))
        return [self._parse_article(article) for article in root.iter("article")]

    def _parse_article(self, article: ET.Element) -> FetchedSource:
        pmcid = self._pmcid(article)
        title = element_text(article.find(".//front//title-group/article-title"))

        documents: list[RawDocument] = []
        ordinal = 0
        if title:
            documents.append(RawDocument(kind="title", text=title, ordinal=ordinal))
            ordinal += 1

        abstract = self._abstract_text(article)
        if abstract:
            documents.append(RawDocument(kind="abstract", text=abstract, ordinal=ordinal))
            ordinal += 1

        for section in self._body_sections(article):
            documents.append(RawDocument(kind="body", text=section, ordinal=ordinal))
            ordinal += 1

        return FetchedSource(
            connector=self.name,
            external_id=pmcid,
            title=title,
            documents=tuple(documents),
            url=(
                f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmcid}/" if pmcid else None
            ),
            license=self._license(article),
            meta=self._meta(article),
        )

    @staticmethod
    def _pmcid(article: ET.Element) -> str:
        for node in article.iterfind(".//front//article-id"):
            if node.get("pub-id-type") in {"pmc", "pmcid"}:
                return element_text(node).removeprefix("PMC")
        return ""

    @staticmethod
    def _abstract_text(article: ET.Element) -> str:
        abstract = article.find(".//front//abstract")
        if abstract is None:
            return ""
        paragraphs = [element_text(p) for p in abstract.iter("p")]
        return "\n\n".join(p for p in paragraphs if p)

    @staticmethod
    def _body_sections(article: ET.Element) -> list[str]:
        """One string per top-level body section: its heading followed by its paragraphs."""
        body = article.find("body")
        if body is None:
            return []
        sections: list[str] = []
        for section in body.findall("sec"):
            heading = element_text(section.find("title"))
            paragraphs = [element_text(p) for p in section.iter("p")]
            block = "\n\n".join(p for p in paragraphs if p)
            if not block:
                continue
            sections.append(f"{heading}\n\n{block}" if heading else block)
        return sections

    @staticmethod
    def _license(article: ET.Element) -> str | None:
        license_node = article.find(".//front//permissions/license")
        if license_node is None:
            return None
        return license_node.get("license-type") or element_text(license_node) or None

    @staticmethod
    def _meta(article: ET.Element) -> dict[str, Any]:
        meta: dict[str, Any] = {}
        journal = element_text(article.find(".//front//journal-title"))
        if journal:
            meta["journal"] = journal
        year = element_text(article.find(".//front//pub-date/year"))
        if year:
            meta["year"] = year
        authors = [
            element_text(contrib.find(".//surname"))
            for contrib in article.iterfind(".//front//contrib[@contrib-type='author']")
            if element_text(contrib.find(".//surname"))
        ]
        if authors:
            meta["authors"] = authors
        return meta
