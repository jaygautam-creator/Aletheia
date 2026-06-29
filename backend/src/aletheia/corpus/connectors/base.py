"""The normalized fetch shape and the connector interface.

A connector does two separable jobs: *parse* raw provider XML into
:class:`FetchedSource` records, and *fetch* that XML over the network. They are split
deliberately — :meth:`SourceConnector.parse` is pure and runs against committed
fixtures in offline CI, while :meth:`SourceConnector.fetch` is the only part that needs
the network. The trust tier is **not** set here; the ingestion pipeline tags everything
a connector produces as curated-corpus evidence (ADR-0003).
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, ClassVar
from xml.etree import ElementTree as ET

import httpx

from aletheia.config import Settings, get_settings

#: NCBI E-utilities efetch endpoint shared by the PubMed and PMC connectors.
EUTILS_EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

#: NCBI asks unauthenticated clients to stay at or below 3 requests/second.
_DEFAULT_REQUEST_INTERVAL = 0.34


@dataclass(frozen=True, slots=True)
class RawDocument:
    """A normalized unit of text within a source (its title, abstract, or a section)."""

    kind: str
    text: str
    ordinal: int = 0


@dataclass(frozen=True, slots=True)
class FetchedSource:
    """A provider-neutral bibliographic record ready for chunking and embedding."""

    connector: str
    external_id: str
    title: str
    documents: tuple[RawDocument, ...]
    url: str | None = None
    license: str | None = None
    meta: Mapping[str, Any] = field(default_factory=dict)


def strip_namespaces(root: ET.Element) -> ET.Element:
    """Drop XML namespaces in place so elements can be matched by local name.

    NCBI payloads mix JATS, MathML, and xlink namespaces; stripping them lets the
    parsers use plain ``find``/``iter`` calls without threading namespace maps through.
    """
    for element in root.iter():
        if isinstance(element.tag, str) and "}" in element.tag:
            element.tag = element.tag.split("}", 1)[1]
    return root


def element_text(element: ET.Element | None) -> str:
    """Flatten an element's full text content (including inline tags), collapsing space."""
    if element is None:
        return ""
    return " ".join("".join(element.itertext()).split())


class SourceConnector(ABC):
    """Fetches and parses one external literature source into :class:`FetchedSource`."""

    #: Stable connector identifier, stored on every source (e.g. ``"pubmed"``).
    name: ClassVar[str]
    #: The E-utilities database this connector reads from (``"pubmed"`` / ``"pmc"``).
    db: ClassVar[str]

    def __init__(self, *, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @abstractmethod
    def parse(self, raw: str, /) -> list[FetchedSource]:
        """Parse a raw provider payload into zero or more normalized sources.

        The payload format is the connector's own — provider XML for the E-utilities
        connectors, JSONL for a bulk corpus file. The parameter is positional-only so
        each connector may name it for its format.
        """

    async def fetch(self, external_ids: Sequence[str]) -> list[FetchedSource]:
        """Fetch the given external IDs from E-utilities and parse the response.

        IDs are requested in a single efetch call; the parser preserves their order.
        """
        ids = [external_id.strip() for external_id in external_ids if external_id.strip()]
        if not ids:
            return []
        raw_xml = await self._efetch(ids)
        return self.parse(raw_xml)

    async def _efetch(self, ids: Sequence[str]) -> str:
        params: dict[str, str] = {
            "db": self.db,
            "id": ",".join(ids),
            "retmode": "xml",
            "tool": "aletheia",
        }
        if self._settings.ncbi_email:
            params["email"] = self._settings.ncbi_email
        if self._settings.ncbi_api_key is not None:
            params["api_key"] = self._settings.ncbi_api_key.get_secret_value()

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(EUTILS_EFETCH, params=params)
            response.raise_for_status()
            # Stay polite to the shared NCBI endpoint between successive batches.
            await asyncio.sleep(_DEFAULT_REQUEST_INTERVAL)
            return response.text
