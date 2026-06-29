"""Public benchmark adapters for the Phase 3 evaluation harness.

Phase 1 (:mod:`aletheia.evaluation.dataset`) ships its own inline evidence; Phase 3
scores verdicts against a *public* claim-verification benchmark while grounding in the
frozen medical corpus (EVALUATION.md §5). This module defines the dataset-agnostic
:class:`BenchmarkItem` and the loader for SciFact, the selected medical set.

SciFact (Wadden et al., *Fact or Fiction: Verifying Scientific Claims*, EMNLP 2020)
verifies expert-written scientific claims against biomedical abstracts. Its claim-level
labels map directly onto the pipeline's own verdict space::

    SUPPORT        -> Verdict.SUPPORTED
    CONTRADICT     -> Verdict.CONTRADICTED
    (no evidence)  -> Verdict.UNVERIFIABLE   # the dataset's NotEnoughInfo

so a SciFact claim is exactly what the pipeline emits a verdict for, and the gold label
and the predicted verdict live in the same three-valued space — compared like with like.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from aletheia.agents.contracts import Verdict


class BenchmarkItem(BaseModel):
    """One benchmark claim, its gold verdict, and the abstracts it cites.

    ``gold`` is expressed in the pipeline's own :class:`Verdict` space so scoring
    compares like with like. ``cited_doc_ids`` names the corpus documents the gold label
    depends on — used to check corpus coverage before a run can be meaningful (a claim
    whose cited abstracts are absent from the corpus can only come back Unverifiable).
    """

    id: str = Field(min_length=1)
    claim: str = Field(min_length=1)
    gold: Verdict = Field(description="The dataset's gold label, in the pipeline's verdict space.")
    cited_doc_ids: list[str] = Field(default_factory=list)
    dataset: str = Field(default="scifact", min_length=1)


def _scifact_gold(evidence: Mapping[str, Sequence[Mapping[str, Any]]]) -> Verdict:
    """Collapse SciFact's per-document, per-sentence evidence into one claim-level label.

    A claim's evidence map is keyed by cited document id; each value lists sentence-level
    annotations carrying a ``label``. A SciFact claim takes a single stance, but we apply
    an explicit precedence defensively: any ``CONTRADICT`` makes the claim contradicted,
    any ``SUPPORT`` makes it supported, and an empty map is NotEnoughInfo (Unverifiable).
    """
    labels = {entry.get("label") for groups in evidence.values() for entry in groups}
    if "CONTRADICT" in labels:
        return Verdict.CONTRADICTED
    if "SUPPORT" in labels:
        return Verdict.SUPPORTED
    return Verdict.UNVERIFIABLE


def parse_scifact_claim(raw: str) -> BenchmarkItem:
    """Parse one line of a SciFact ``claims`` JSONL file into a :class:`BenchmarkItem`."""
    data: dict[str, Any] = json.loads(raw)
    evidence = data.get("evidence") or {}
    return BenchmarkItem(
        id=str(data["id"]),
        claim=data["claim"],
        gold=_scifact_gold(evidence),
        cited_doc_ids=[str(doc_id) for doc_id in data.get("cited_doc_ids", [])],
    )


def load_scifact_claims(path: str | Path) -> list[BenchmarkItem]:
    """Load and validate a SciFact ``claims`` JSONL file (e.g. ``claims_dev.jsonl``).

    Blank lines are skipped. Raises if the file yields no claims, so an empty or
    mis-pathed dataset fails loudly rather than silently scoring nothing.
    """
    text = Path(path).read_text("utf-8")
    items = [parse_scifact_claim(line) for line in text.splitlines() if line.strip()]
    if not items:
        raise ValueError(f"No SciFact claims found in {path}.")
    return items
