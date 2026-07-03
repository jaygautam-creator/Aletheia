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
import random
from collections.abc import Mapping, Sequence
from collections.abc import Set as AbstractSet
from dataclasses import dataclass
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


def stratified_sample(items: Sequence[BenchmarkItem], n: int, *, seed: int) -> list[BenchmarkItem]:
    """Draw a seeded, label-stratified sample of ``n`` items without replacement.

    Allocation is proportional to each gold label's share of ``items`` (EVALUATION.md §5),
    so the sample preserves the benchmark's Supported/Contradicted/Unverifiable mix
    instead of whatever bias a head-slice happens to carry. The flooring remainder goes
    to the largest stratum (spilling to the next largest when one is exhausted), and the
    draw within each stratum uses ``random.Random(seed)`` — a given ``(items, n, seed)``
    always yields the same sample. Selected items keep their original dataset order;
    ``n >= len(items)`` returns every item.
    """
    if n < 0:
        raise ValueError("Sample size must be non-negative.")
    if n >= len(items):
        return list(items)
    strata: dict[Verdict, list[int]] = {verdict: [] for verdict in Verdict}
    for index, item in enumerate(items):
        strata[item.gold].append(index)
    quotas = {verdict: n * len(members) // len(items) for verdict, members in strata.items()}
    remainder = n - sum(quotas.values())
    for verdict in sorted(strata, key=lambda label: len(strata[label]), reverse=True):
        take = min(remainder, len(strata[verdict]) - quotas[verdict])
        quotas[verdict] += take
        remainder -= take
    rng = random.Random(seed)
    chosen: list[int] = []
    for verdict in Verdict:  # fixed draw order keeps the rng sequence deterministic
        chosen.extend(rng.sample(strata[verdict], quotas[verdict]))
    return [items[index] for index in sorted(chosen)]


@dataclass(frozen=True, slots=True)
class Coverage:
    """How much of a claim set's cited evidence the ingested corpus can actually serve.

    An item is *covered* when every document its gold label cites is present in the
    corpus. Coverage below ~95% makes a run's numbers suspect: a claim whose cited
    abstracts are missing can only ever come back Unverifiable, deflating every system
    at once (see :class:`BenchmarkItem`).
    """

    n_items: int
    n_covered: int

    @property
    def fraction(self) -> float:
        """The covered share; an empty claim set is vacuously fully covered."""
        return self.n_covered / self.n_items if self.n_items else 1.0


def coverage_against(items: Sequence[BenchmarkItem], ingested_ids: AbstractSet[str]) -> Coverage:
    """Check which items have *all* their cited documents among ``ingested_ids``.

    Pure set logic, unit-testable offline; the database query that produces
    ``ingested_ids`` lives with the runner. An item with no cited documents (an
    Unverifiable claim) is trivially covered — its gold label depends on no abstract.
    """
    covered = sum(
        1 for item in items if all(doc_id in ingested_ids for doc_id in item.cited_doc_ids)
    )
    return Coverage(n_items=len(items), n_covered=covered)
