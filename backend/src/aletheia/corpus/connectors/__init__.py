"""Source connectors: fetch and normalize external literature into the corpus shape.

A connector knows how to turn one external bibliographic source (a PubMed abstract, a
PMC open-access article) into a provider-neutral :class:`FetchedSource` — the input the
ingestion pipeline chunks, embeds, and stores. Parsing is kept separate from network
fetching so the parsers can be tested entirely offline against committed fixtures.
"""

from aletheia.corpus.connectors.base import (
    FetchedSource,
    RawDocument,
    SourceConnector,
)
from aletheia.corpus.connectors.pmc import PmcConnector
from aletheia.corpus.connectors.pubmed import PubMedConnector

#: Connectors keyed by their stable name, for the ingestion CLI and tests.
CONNECTORS: dict[str, type[SourceConnector]] = {
    PubMedConnector.name: PubMedConnector,
    PmcConnector.name: PmcConnector,
}

__all__ = [
    "CONNECTORS",
    "FetchedSource",
    "PmcConnector",
    "PubMedConnector",
    "RawDocument",
    "SourceConnector",
]
