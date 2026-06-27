"""A deterministic, offline LLM client for tests and key-free runs.

Real provider calls are non-deterministic and need a paid-or-rate-limited key, so
they have no place in CI. ``FakeLLMClient`` returns scripted responses, records the
prompts it received, and counts tokens deterministically — enough to exercise every
node, the graph, and the API without touching the network.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Sequence

from aletheia.llm.base import LLMClient, LLMError, LLMResponse, Message, TokenUsage

#: A function that produces a reply from the prompt — for content-aware fakes.
ResponseRouter = Callable[[Sequence[Message], bool], str]


def _count_tokens(text: str) -> int:
    """A stable, whitespace-based token estimate (no model or network needed)."""
    return len(text.split())


class FakeLLMClient(LLMClient):
    """A scripted :class:`LLMClient`.

    Configure it one of three ways:

    * a single ``str`` — returned for every call;
    * a sequence of ``str`` — returned in order (exhaustion raises, surfacing an
      unexpected extra call);
    * a :data:`ResponseRouter` callable ``(messages, json_mode) -> str`` — for
      replies that depend on the prompt.
    """

    provider = "fake"

    def __init__(
        self,
        responses: str | Sequence[str] | ResponseRouter,
        *,
        model: str = "fake-1",
    ) -> None:
        super().__init__(model=model)
        self.calls: list[list[Message]] = []
        self._router: ResponseRouter | None = None
        self._queue: deque[str] | None = None

        if callable(responses):
            self._router = responses
        elif isinstance(responses, str):
            self._router = lambda _messages, _json_mode: responses
        else:
            self._queue = deque(responses)

    async def complete(
        self,
        messages: Sequence[Message],
        *,
        temperature: float = 0.0,
        json_mode: bool = False,
    ) -> LLMResponse:
        self.calls.append(list(messages))

        if self._router is not None:
            text = self._router(messages, json_mode)
        else:
            assert self._queue is not None  # guaranteed by __init__
            if not self._queue:
                raise LLMError("FakeLLMClient ran out of scripted responses.")
            text = self._queue.popleft()

        prompt_tokens = sum(_count_tokens(m.content) for m in messages)
        return LLMResponse(
            text=text,
            model=self.model,
            usage=TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=_count_tokens(text),
            ),
        )

    @property
    def call_count(self) -> int:
        """How many times :meth:`complete` has been called."""
        return len(self.calls)
