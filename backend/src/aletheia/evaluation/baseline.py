"""The single-LLM baseline — the comparison point for the grounded system.

This is the "single model checks the answer" condition: one LLM call judges every claim
against the evidence at once, with no requirement to quote a span and no per-claim
isolation. Holding the model, prompt budget, and evidence fixed, the *only* thing that
differs from the grounded verifier is the verification architecture — so the gap between
them isolates the contribution of evidence-grounded, per-claim verification.
"""

from __future__ import annotations

from aletheia.evaluation.dataset import DatasetItem
from aletheia.llm import LLMClient, LLMError, Message

_BASELINE = (
    "You verify a candidate answer against evidence. You are given a numbered list of "
    "atomic claims. For each claim, decide whether the evidence supports it. Return JSON "
    "only: a 'labels' array of the same length and order as the claims, where each entry "
    'is exactly "Supported" or "Unsupported": {"labels": ["Supported"|"Unsupported", ...]}.'
)


def _parse_labels(data: object, expected: int) -> list[bool]:
    if not isinstance(data, dict):
        raise LLMError(f"Baseline expected a JSON object, got {type(data).__name__}.")
    labels = data.get("labels")
    if not isinstance(labels, list):
        raise LLMError("Baseline response is missing a 'labels' array.")
    if len(labels) != expected:
        raise LLMError(f"Baseline returned {len(labels)} labels for {expected} claims.")
    return [isinstance(label, str) and label.strip().lower() == "supported" for label in labels]


async def baseline_supported(llm: LLMClient, item: DatasetItem) -> list[bool]:
    """Return, per claim, whether the single-LLM baseline judged it supported."""
    numbered = "\n".join(f"{i}. {claim.text}" for i, claim in enumerate(item.claims, start=1))
    user = (
        f"Question: {item.question}\n\n"
        f"EVIDENCE:\n{item.evidence}\n\n"
        f"CLAIMS ({len(item.claims)}):\n{numbered}"
    )
    data = await llm.generate_json([Message.system(_BASELINE), Message.user(user)])
    return _parse_labels(data, len(item.claims))
