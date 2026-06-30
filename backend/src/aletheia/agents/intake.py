"""The intake guard — the pipeline's first line of defence.

Aletheia only verifies biomedical and health-related claims, and it must not be steered
off task by inputs that try to override its instructions. This guard runs *before* any
answer is generated and decides whether to admit a query:

* a deterministic scan rejects common prompt-injection / jailbreak patterns outright —
  it makes no model call, so it cannot itself be talked out of refusing;
* an LLM scope classifier then judges whether the topic is medical/health at all.

A rejected query never reaches the Generator: the graph routes straight to a refusal,
so off-topic or adversarial input is declined with a clear reason instead of answered.
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
    "This question is outside Aletheia's scope. Aletheia only verifies medical and "
    "health-related claims against the medical literature."
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
            return {
                "intake": IntakeDecision(
                    allowed=False, category="out_of_scope", reason=_OUT_OF_SCOPE_REASON
                )
            }
        return {"intake": IntakeDecision(allowed=True, category="ok", reason="in scope")}

    return intake
