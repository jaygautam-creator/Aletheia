"""An :class:`LLMClient` decorator that records token usage and latency per call.

The agents call :meth:`LLMClient.generate_json`, which discards the provider's usage;
wrapping the client at the :meth:`complete` boundary captures every call's tokens and
wall-clock without changing the interface the agents use or the verdicts they produce.
The evaluation harness wraps the real client with this to feed the cost and trace
dimensions of a benchmark run.
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import dataclass

from aletheia.llm.base import LLMClient, LLMResponse, Message, TokenUsage


@dataclass(frozen=True, slots=True)
class CallRecord:
    """One :meth:`complete` call: the model, its token usage, and how long it took."""

    model: str
    prompt_tokens: int
    completion_tokens: int
    latency_s: float

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @property
    def usage(self) -> TokenUsage:
        return TokenUsage(self.prompt_tokens, self.completion_tokens)


class RecordingLLMClient(LLMClient):
    """Wraps an :class:`LLMClient`, recording each call's usage and latency.

    The wrapped client's output is returned unchanged, so the agents behave identically;
    only the instrumentation is added. Because :meth:`generate_json` is inherited and
    routes through this :meth:`complete`, usage is captured even though callers use the
    JSON helper that would otherwise drop it.
    """

    def __init__(self, delegate: LLMClient) -> None:
        super().__init__(model=delegate.model)
        self._delegate = delegate
        self.records: list[CallRecord] = []

    @property
    def provider(self) -> str:  # type: ignore[override]  # a read-only view of the delegate's
        return self._delegate.provider

    async def complete(
        self,
        messages: Sequence[Message],
        *,
        temperature: float = 0.0,
        json_mode: bool = False,
    ) -> LLMResponse:
        start = time.perf_counter()
        response = await self._delegate.complete(
            messages, temperature=temperature, json_mode=json_mode
        )
        elapsed = time.perf_counter() - start
        usage = response.usage or TokenUsage()
        self.records.append(
            CallRecord(
                model=response.model,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                latency_s=elapsed,
            )
        )
        return response

    @property
    def usages(self) -> list[TokenUsage]:
        """One :class:`TokenUsage` per recorded call — feeds ``cost_from_usages``."""
        return [record.usage for record in self.records]

    @property
    def total_usage(self) -> TokenUsage:
        """Summed token usage across all recorded calls."""
        return TokenUsage(
            prompt_tokens=sum(record.prompt_tokens for record in self.records),
            completion_tokens=sum(record.completion_tokens for record in self.records),
        )

    def reset(self) -> None:
        """Drop recorded calls — e.g. between queries in a benchmark sweep."""
        self.records.clear()
