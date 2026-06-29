"""Tests for the deterministic chunker — pure functions, no I/O."""

from __future__ import annotations

import pytest

from aletheia.corpus.chunking import chunk_text


def test_short_text_is_a_single_chunk() -> None:
    assert chunk_text("aspirin reduces fever") == ["aspirin reduces fever"]


def test_whitespace_is_normalized() -> None:
    assert chunk_text("  aspirin\n\n  reduces   fever \t") == ["aspirin reduces fever"]


def test_empty_or_blank_text_yields_no_chunks() -> None:
    assert chunk_text("") == []
    assert chunk_text("   \n\t ") == []


def test_long_text_is_split_within_budget() -> None:
    text = " ".join(f"word{i}" for i in range(200))
    chunks = chunk_text(text, max_chars=100, overlap=20)

    assert len(chunks) > 1
    assert all(len(chunk) <= 100 for chunk in chunks)
    # No words are lost or split: every original word appears across the chunks.
    recovered = {word for chunk in chunks for word in chunk.split(" ")}
    assert recovered == {f"word{i}" for i in range(200)}


def test_chunks_overlap_at_the_boundary() -> None:
    text = " ".join(f"w{i:03d}" for i in range(60))
    chunks = chunk_text(text, max_chars=40, overlap=15)

    # The tail of one chunk reappears at the head of the next.
    first_tail = chunks[0].split(" ")[-1]
    assert first_tail in chunks[1].split(" ")


def test_split_always_makes_progress_with_long_words() -> None:
    # A single word longer than the budget is taken whole rather than looping forever.
    chunks = chunk_text("short " + "x" * 50 + " tail", max_chars=10, overlap=3)
    assert "x" * 50 in chunks
    two_long_words = chunk_text("aaaaaaaaaa bbbbbbbbbb", max_chars=5, overlap=0)
    assert two_long_words == ["aaaaaaaaaa", "bbbbbbbbbb"]


def test_chunking_is_deterministic() -> None:
    text = " ".join(f"token{i}" for i in range(120))
    assert chunk_text(text, max_chars=80, overlap=20) == chunk_text(text, max_chars=80, overlap=20)


@pytest.mark.parametrize(
    ("max_chars", "overlap"),
    [(0, 0), (-1, 0), (100, 100), (100, 150), (100, -1)],
)
def test_invalid_parameters_are_rejected(max_chars: int, overlap: int) -> None:
    with pytest.raises(ValueError):
        chunk_text("some text", max_chars=max_chars, overlap=overlap)
