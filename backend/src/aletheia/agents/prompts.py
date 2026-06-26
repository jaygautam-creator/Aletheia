"""Prompt templates for the Generator and Verifier.

Prompts are kept in one place, version-controlled and reviewable, because they are
part of the experimental method: the evaluation harness holds them fixed across the
single-LLM baseline and the multi-agent system so the only thing that varies is the
architecture. The Verifier prompt in particular is load-bearing — it is where the
"quote an exact span or answer Unverifiable" discipline is imposed.
"""

from __future__ import annotations

from collections.abc import Sequence

from aletheia.llm import Message

# --- Generator ---------------------------------------------------------------

_GENERATE_AND_DECOMPOSE = (
    "You are a careful research assistant. Answer the user's question concisely and "
    "factually, then break your answer into atomic, independently checkable claims.\n"
    "An atomic claim is a single self-contained statement that asserts one fact and "
    "can be judged true or false on its own.\n"
    'Respond with JSON only: {"answer": string, "claims": [string, ...]}.'
)

_DECOMPOSE_ONLY = (
    "You decompose an existing answer into atomic, independently checkable claims. "
    "An atomic claim is a single self-contained statement that asserts one fact and "
    "can be judged true or false on its own.\n"
    "Use only information present in the answer; do not add, infer, or correct facts.\n"
    'Respond with JSON only: {"claims": [string, ...]}.'
)


def generate_messages(query: str) -> Sequence[Message]:
    """Prompt to produce a candidate answer and its atomic claims."""
    return [Message.system(_GENERATE_AND_DECOMPOSE), Message.user(f"Question: {query}")]


def decompose_messages(query: str, answer: str) -> Sequence[Message]:
    """Prompt to decompose a pre-supplied candidate answer into atomic claims."""
    return [
        Message.system(_DECOMPOSE_ONLY),
        Message.user(f"Question: {query}\n\nAnswer to decompose:\n{answer}"),
    ]


# --- Verifier ----------------------------------------------------------------

_VERIFY = (
    "You are a strict verification critic. Judge a single CLAIM using ONLY the "
    "provided EVIDENCE — never your own knowledge. Choose exactly one verdict:\n"
    '- "Supported": the evidence explicitly supports the claim. You MUST quote the '
    "exact span of evidence that supports it.\n"
    '- "Contradicted": the evidence explicitly contradicts the claim. You MUST quote '
    "the exact span of evidence that contradicts it.\n"
    '- "Unverifiable": the evidence neither supports nor contradicts the claim. Do '
    "NOT quote a span.\n"
    "The quoted span must be copied verbatim, character for character, from the "
    "EVIDENCE. If you cannot find such a span, you must answer Unverifiable.\n"
    'Respond with JSON only: {"verdict": "Supported"|"Contradicted"|"Unverifiable", '
    '"quoted_span": string|null, "reasoning": string}.'
)


def verify_messages(claim: str, evidence: str) -> Sequence[Message]:
    """Prompt to judge one claim against the evidence with a forced span."""
    return [
        Message.system(_VERIFY),
        Message.user(f"EVIDENCE:\n{evidence}\n\nCLAIM:\n{claim}"),
    ]
