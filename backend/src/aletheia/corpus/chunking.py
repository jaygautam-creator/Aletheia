"""Deterministic, word-aware text chunking for the corpus.

Embedding models have a bounded context and retrieval is sharper over focused spans, so
documents are split into overlapping chunks before embedding. The split is a sliding
window over whitespace-delimited words: it never cuts a word in half, the overlap keeps
a claim that straddles a boundary retrievable from either chunk, and the same input
always yields the same chunks — a precondition for the reproducible frozen corpus
(ADR-0006).
"""

from __future__ import annotations

from dataclasses import dataclass

#: Default chunk budget and overlap, in characters. ~1000 chars (roughly 150-200 tokens)
#: sits inside bge-small's window while staying specific enough to retrieve well.
DEFAULT_CHUNK_CHARS = 1000
DEFAULT_CHUNK_OVERLAP = 150


@dataclass(frozen=True, slots=True)
class ChunkConfig:
    """The chunking knobs, bundled so they travel as one argument through the pipeline."""

    max_chars: int = DEFAULT_CHUNK_CHARS
    overlap: int = DEFAULT_CHUNK_OVERLAP


#: Module-level default so callers can take a shared, immutable config as a default
#: argument without constructing one in the signature (which the linter rightly flags).
DEFAULT_CHUNKING = ChunkConfig()


def chunk_text(
    text: str,
    *,
    max_chars: int = DEFAULT_CHUNK_CHARS,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[str]:
    """Split ``text`` into overlapping, word-aligned chunks of at most ``max_chars``.

    Whitespace is normalized first. Text within the budget returns as a single chunk.
    ``overlap`` is the approximate number of trailing characters repeated at the start of
    the next chunk; it must be smaller than ``max_chars``.
    """
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    if not 0 <= overlap < max_chars:
        raise ValueError("overlap must be in [0, max_chars)")

    normalized = " ".join(text.split())
    if not normalized:
        return []
    if len(normalized) <= max_chars:
        return [normalized]

    words = normalized.split(" ")
    chunks: list[str] = []
    start = 0
    while start < len(words):
        window, end = _take_window(words, start, max_chars)
        chunks.append(" ".join(window))
        if end >= len(words):
            break
        start = end - _overlap_words(window, overlap)
    return chunks


def _take_window(words: list[str], start: int, max_chars: int) -> tuple[list[str], int]:
    """Greedily pack words from ``start`` until the char budget is reached."""
    window: list[str] = []
    length = 0
    index = start
    while index < len(words):
        addition = len(words[index]) + (1 if window else 0)
        if window and length + addition > max_chars:
            break
        window.append(words[index])
        length += addition
        index += 1
    # A single word longer than the budget is taken whole rather than dropped.
    if not window:
        return [words[start]], start + 1
    return window, index


def _overlap_words(window: list[str], overlap: int) -> int:
    """How many trailing words of ``window`` to repeat to cover ~``overlap`` chars.

    Capped at ``len(window) - 1`` so the next window always advances by at least one word.
    """
    repeated = 0
    length = 0
    while repeated < len(window) - 1:
        length += len(window[-1 - repeated]) + 1
        if length > overlap:
            break
        repeated += 1
    return repeated
