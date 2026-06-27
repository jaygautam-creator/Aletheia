"""The evidence corpus: its schema and (later) ingestion and retrieval.

The corpus is the high-trust foundation Aletheia grounds verdicts in (ADR-0003). This
package holds the relational + vector schema; ingestion connectors and hybrid
retrieval are added on top of it in subsequent Phase 2 workstreams.
"""

from aletheia.corpus.models import EMBEDDING_DIM, Chunk, Document, Source, TrustTier

__all__ = ["EMBEDDING_DIM", "Chunk", "Document", "Source", "TrustTier"]
