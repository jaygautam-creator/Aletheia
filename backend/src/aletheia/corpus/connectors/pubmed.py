"""PubMed connector — title and (possibly structured) abstract from a PMID.

PubMed records expose a citation's title and abstract but not full text. We normalize
each ``PubmedArticle`` into a title document and an abstract document, preserving the
section labels of a structured abstract (e.g. ``BACKGROUND``, ``METHODS``) so the text
the Verifier later quotes keeps its original framing. Journal, year, and author surnames
are kept as provenance metadata.
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


class PubMedConnector(SourceConnector):
    """Normalizes PubMed citation XML into :class:`FetchedSource` records."""

    name = "pubmed"
    db = "pubmed"

    def parse(self, raw_xml: str) -> list[FetchedSource]:
        root = strip_namespaces(ET.fromstring(raw_xml))
        return [self._parse_article(article) for article in root.iter("PubmedArticle")]

    def _parse_article(self, article: ET.Element) -> FetchedSource:
        pmid = element_text(article.find(".//MedlineCitation/PMID"))
        title = element_text(article.find(".//Article/ArticleTitle"))

        documents: list[RawDocument] = []
        if title:
            documents.append(RawDocument(kind="title", text=title, ordinal=0))
        abstract = self._abstract_text(article)
        if abstract:
            documents.append(RawDocument(kind="abstract", text=abstract, ordinal=1))

        return FetchedSource(
            connector=self.name,
            external_id=pmid,
            title=title,
            documents=tuple(documents),
            url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None,
            meta=self._meta(article),
        )

    @staticmethod
    def _abstract_text(article: ET.Element) -> str:
        """Join the abstract's sections, prefixing each with its label when present."""
        parts: list[str] = []
        for node in article.iterfind(".//Article/Abstract/AbstractText"):
            text = element_text(node)
            if not text:
                continue
            label = node.get("Label")
            parts.append(f"{label}: {text}" if label else text)
        return "\n\n".join(parts)

    @staticmethod
    def _meta(article: ET.Element) -> dict[str, Any]:
        meta: dict[str, Any] = {}
        journal = element_text(article.find(".//Article/Journal/Title"))
        if journal:
            meta["journal"] = journal
        year = element_text(article.find(".//Article/Journal/JournalIssue/PubDate/Year"))
        if year:
            meta["year"] = year
        authors = [
            element_text(name.find("LastName"))
            for name in article.iterfind(".//Article/AuthorList/Author")
            if element_text(name.find("LastName"))
        ]
        if authors:
            meta["authors"] = authors
        return meta
