"""Integrity tests for the curated Phase 1 mini-dataset."""

from __future__ import annotations

from aletheia.evaluation import load_mini_dataset


def test_dataset_loads_and_validates() -> None:
    items = load_mini_dataset()

    assert len(items) >= 8
    assert len({item.id for item in items}) == len(items), "item ids must be unique"


def test_every_item_has_both_supported_and_planted_claims() -> None:
    for item in load_mini_dataset():
        labels = item.gold_supported
        assert any(labels), f"{item.id} has no supported claims"
        assert not all(labels), f"{item.id} has no planted unsupported claim"


def test_supported_claims_are_groundable_in_the_evidence() -> None:
    # A supported claim should share substantial vocabulary with the evidence, so the
    # grounded verifier has a real span to quote. This guards against authoring a
    # 'supported' label the evidence cannot actually back.
    for item in load_mini_dataset():
        evidence_words = {w.strip(".,").lower() for w in item.evidence.split()}
        for claim in item.claims:
            if not claim.supported:
                continue
            claim_words = {w.strip(".,").lower() for w in claim.text.split() if len(w) > 3}
            overlap = claim_words & evidence_words
            assert len(overlap) >= 2, f"{item.id}: weakly grounded supported claim: {claim.text}"
