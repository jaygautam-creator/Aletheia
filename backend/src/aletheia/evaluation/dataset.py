"""The Phase 1 mini-dataset: typed items loaded from packaged JSONL.

Each item pairs a short evidence passage with a candidate answer that has been broken
into atomic claims and labelled against the evidence. Some claims are deliberately
*planted* — unsupported by the evidence (either contradicted or simply absent) — so the
dataset can measure whether a system flags them. Crucially, "supported" means supported
*by the evidence*, not by world knowledge: a true fact the passage does not state is
still unsupported, because grounded verification can only stand on the evidence.
"""

from __future__ import annotations

from importlib import resources

from pydantic import BaseModel, Field

_DATASET_RESOURCE = "phase1_mini.jsonl"


class GoldClaim(BaseModel):
    """One atomic claim and its gold label relative to the evidence."""

    text: str = Field(min_length=1)
    supported: bool = Field(description="True iff the evidence supports the claim.")


class DatasetItem(BaseModel):
    """A question, its evidence, a candidate answer, and labelled atomic claims."""

    id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    evidence: str = Field(min_length=1)
    candidate_answer: str = Field(min_length=1)
    claims: list[GoldClaim] = Field(min_length=1)

    @property
    def claim_texts(self) -> list[str]:
        return [claim.text for claim in self.claims]

    @property
    def gold_supported(self) -> list[bool]:
        return [claim.supported for claim in self.claims]


def load_mini_dataset() -> list[DatasetItem]:
    """Load and validate the curated Phase 1 dataset shipped with the package."""
    raw = (
        resources.files("aletheia.evaluation")
        .joinpath("data", _DATASET_RESOURCE)
        .read_text("utf-8")
    )
    items = [DatasetItem.model_validate_json(line) for line in raw.splitlines() if line.strip()]
    if not items:
        raise ValueError("Phase 1 dataset is empty.")
    return items
