"""An :class:`LLMClient` decorator that fails over across providers.

Each provider adapter already retries its own transient blips (timeouts, 5xx, rate
limits) with bounded backoff. That is not enough when a provider is *exhausted* — a
daily token cap hit mid-run, or a sustained outage — because every retry hits the
same dead end. Aletheia's evaluation harness makes hundreds of calls per sweep, and a
single such failure used to abort the whole run.

:class:`FallbackLLMClient` wraps an ordered chain of clients. It returns the first
one's reply, and on an :class:`LLMError` it falls over to the next, only surfacing a
failure when every provider in the chain is exhausted. The verdict contract is
unchanged: callers still see a single :class:`LLMClient`, and the model that actually
answered is carried on the :class:`~aletheia.llm.base.LLMResponse`, so cost accounting
attributes tokens to the provider that did the work.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Sequence
from typing import Any, TypeVar

from aletheia.llm.base import LLMClient, LLMError, LLMResponse, Message

logger = logging.getLogger(__name__)

_T = TypeVar("_T")


class FallbackLLMClient(LLMClient):
    """Tries an ordered chain of clients, falling over to the next on :class:`LLMError`.

    The head of the chain is the primary provider; the remainder are fallbacks tried in
    order. :attr:`provider` and :attr:`model` reflect the primary, for identification;
    the provider that ultimately answers is reported on its response.
    """

    def __init__(self, clients: Sequence[LLMClient]) -> None:
        if not clients:
            raise ValueError("FallbackLLMClient needs at least one client.")
        self._clients = list(clients)
        super().__init__(model=self._clients[0].model)

    @property
    def provider(self) -> str:  # type: ignore[override]  # a read-only view of the primary's
        return self._clients[0].provider

    async def complete(
        self,
        messages: Sequence[Message],
        *,
        temperature: float = 0.0,
        json_mode: bool = False,
    ) -> LLMResponse:
        return await self._first_success(
            lambda client: client.complete(messages, temperature=temperature, json_mode=json_mode)
        )

    async def generate_json(
        self,
        messages: Sequence[Message],
        *,
        temperature: float = 0.0,
    ) -> Any:
        # Override so a provider that returns unparseable JSON also triggers fallback,
        # not just one that fails the underlying request.
        return await self._first_success(
            lambda client: client.generate_json(messages, temperature=temperature)
        )

    async def _first_success(self, call: Callable[[LLMClient], Awaitable[_T]]) -> _T:
        """Run ``call`` against each client in turn; return the first success.

        Re-raises the last :class:`LLMError` only when the whole chain is exhausted.
        """
        last_error: LLMError | None = None
        for index, client in enumerate(self._clients):
            try:
                return await call(client)
            except LLMError as exc:
                last_error = exc
                remaining = len(self._clients) - index - 1
                if remaining:
                    logger.warning(
                        "LLM provider %r (%s) failed: %s — falling over to the next of "
                        "%d remaining.",
                        client.provider,
                        client.model,
                        exc,
                        remaining,
                    )
        assert last_error is not None  # the loop runs at least once (clients is non-empty)
        raise last_error
