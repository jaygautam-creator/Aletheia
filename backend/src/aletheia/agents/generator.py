"""The Generator node.

Responsibility: turn the query into a candidate answer and a list of atomic,
independently checkable claims. If a candidate answer is already supplied (as in the
controlled evaluation, where the answer under test is fixed), the Generator decomposes
that answer rather than inventing a new one; otherwise it produces one and decomposes
it in a single call.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from aletheia.agents.prompts import decompose_messages, generate_messages
from aletheia.agents.state import PipelineState
from aletheia.llm import LLMClient, LLMError

GeneratorNode = Callable[[PipelineState], Awaitable[PipelineState]]


def _as_claims(value: object) -> list[str]:
    """Coerce the model's ``claims`` field into a clean list of non-empty strings."""
    if not isinstance(value, list):
        raise LLMError(f"Generator expected a list of claims, got {type(value).__name__}.")
    claims = [item.strip() for item in value if isinstance(item, str) and item.strip()]
    if not claims:
        raise LLMError("Generator returned no usable claims.")
    return claims


def _as_answer(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LLMError("Generator returned no usable answer.")
    return value.strip()


def make_generator_node(llm: LLMClient) -> GeneratorNode:
    """Build the Generator node bound to a specific LLM client."""

    async def generator(state: PipelineState) -> PipelineState:
        query = state["query"]
        provided = state.get("candidate_answer")

        if provided is not None:
            data = await llm.generate_json(decompose_messages(query, provided))
            answer = provided
        else:
            data = await llm.generate_json(generate_messages(query))
            answer = _as_answer(data.get("answer"))

        return {"candidate_answer": answer, "claims": _as_claims(data.get("claims"))}

    return generator
