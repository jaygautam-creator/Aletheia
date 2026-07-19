"""The intake guard — the pipeline's first line of defence.

Aletheia's curated corpus is biomedical, and the pipeline must not be steered off task
by inputs that try to override its instructions. This guard runs *before* any answer is
generated and classifies a query into one of three routes:

* a deterministic scan rejects common prompt-injection / jailbreak patterns outright —
  it makes no model call, so it cannot itself be talked out of refusing — this is the
  only case that actually terminates in a refusal;
* an LLM scope classifier then judges whether the topic is medical/health at all. A
  medical topic proceeds to the curated corpus as always; a general, non-medical topic
  is **not** refused — it is routed to the live Wikipedia fallback instead (ADR-0012).

The scope rule guards the *corpus*, not the engine: when the caller supplies their own
evidence the corpus is never consulted, so any topic may be verified against that
document and the classifier is skipped (ADR-0010). The injection scan always runs.

Only an injection match reaches the refusal node; every other query — medical or
general — proceeds through the full pipeline, just against a different evidence source.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

from aletheia.agents.prompts import classify_scope_messages
from aletheia.llm import LLMClient, LLMError

if TYPE_CHECKING:
    # Typing-only: state.py imports IntakeDecision (below) at runtime, so a runtime import
    # of PipelineState here would be circular. Annotations are lazy under `from __future__`.
    from collections.abc import Awaitable, Callable

    from aletheia.agents.state import PipelineState

    IntakeNode = Callable[[PipelineState], Awaitable[PipelineState]]

logger = logging.getLogger(__name__)

IntakeCategory = Literal["ok", "out_of_scope", "injection"]

# Common prompt-injection / instruction-override patterns. Deliberately conservative:
# genuine medical questions do not phrase themselves this way, so false positives are
# unlikely. Matched case-insensitively anywhere in the input.
_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bignore\s+(?:all\s+|any\s+|the\s+)?(?:previous|prior|above|earlier)\b"
        r".*\b(?:instruction|prompt|message|rule)",
        r"\bdisregard\s+(?:all\s+|any\s+|the\s+|your\s+|previous\s+)*"
        r"(?:instruction|prompt|rule|guideline)",
        r"\bforget\s+(?:everything|all|your|the|previous)\b.*\b(?:instruction|prompt|rule|said)",
        r"\byou\s+are\s+now\b",
        r"\bpretend\s+(?:to\s+be|you\s+are)\b",
        r"\bact\s+as\s+(?:a\s+|an\s+)?(?:dan|jailbreak|unrestricted|different)\b",
        r"\b(?:reveal|show|print|repeat|leak)\b.*\b(?:system\s+)?(?:prompt|instructions)\b",
        r"\bdeveloper\s+mode\b",
        r"\bjailbreak\b",
        r"\bdo\s+anything\s+now\b",
        r"\boverride\s+(?:your|the|all)?\s*(?:instruction|rule|guardrail|safety)",
        r"\bbypass\s+(?:your|the|all)?\s*(?:instruction|rule|guardrail|filter|safety)",
        r"\bnew\s+instructions?\s*:",
        r"\bsystem\s+prompt\b",
    )
)

_OUT_OF_SCOPE_REASON = (
    "This is a general question outside the medical corpus, so it is being checked "
    "against a live Wikipedia lookup instead — a clearly lower-trust source than the "
    "curated medical literature (ADR-0012)."
)
_INJECTION_REASON = (
    "This request looked like an attempt to change the system's instructions, so it was "
    "not processed. Please ask a medical or health-related question instead."
)


class IntakeDecision(BaseModel):
    """The guard's ruling on whether a query may proceed through the pipeline."""

    allowed: bool = Field(description="Whether the query may proceed to generation.")
    category: IntakeCategory = Field(description="ok, out_of_scope, or injection.")
    reason: str = Field(description="One-sentence, user-facing explanation.")


def scan_for_injection(text: str) -> str | None:
    """Return a short reason if ``text`` matches a known injection pattern, else ``None``."""
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            return _INJECTION_REASON
    return None


def make_intake_node(llm: LLMClient) -> IntakeNode:
    """Build the intake guard node bound to a specific LLM client.

    Order matters: the deterministic injection scan runs first (it needs no model and
    cannot be argued with), then the LLM scope classifier. If the classifier itself
    fails or returns something unusable, the guard **fails open** — the downstream
    Verifier still refuses to affirm any claim it cannot ground, so an admitted off-topic
    query degrades to ``Unverifiable``, never to a fabricated medical answer.
    """

    async def intake(state: PipelineState) -> PipelineState:
        query = state["query"]

        if scan_for_injection(query) is not None:
            logger.warning("intake: blocked a possible prompt-injection attempt")
            return {
                "intake": IntakeDecision(
                    allowed=False, category="injection", reason=_INJECTION_REASON
                )
            }

        # The intake node runs before the Retriever, so ``evidence`` present here can
        # only be caller-supplied: the corpus will not be consulted, the medical-scope
        # rule does not apply, and any topic may be judged against that document
        # (ADR-0010). The injection scan above has already run.
        if state.get("evidence"):
            return {
                "intake": IntakeDecision(
                    allowed=True, category="ok", reason="caller-supplied evidence"
                )
            }

        try:
            data = await llm.generate_json(classify_scope_messages(query))
        except LLMError:
            logger.warning("intake: scope classifier unavailable; admitting query (fail-open)")
            return {
                "intake": IntakeDecision(
                    allowed=True, category="ok", reason="scope check unavailable"
                )
            }

        if not isinstance(data, dict):
            logger.warning("intake: scope classifier returned a non-object; admitting (fail-open)")
            return {
                "intake": IntakeDecision(
                    allowed=True, category="ok", reason="scope check inconclusive"
                )
            }

        if not bool(data.get("in_scope")):
            # Unlike an injection attempt, a general question is not refused (ADR-0012):
            # it is admitted with category="out_of_scope", which the Retriever node reads
            # to route to the live Wikipedia fallback instead of the medical corpus.
            return {
                "intake": IntakeDecision(
                    allowed=True, category="out_of_scope", reason=_OUT_OF_SCOPE_REASON
                )
            }
        return {"intake": IntakeDecision(allowed=True, category="ok", reason="in scope")}

    return intake
