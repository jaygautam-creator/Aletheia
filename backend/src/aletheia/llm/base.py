"""The provider-agnostic LLM interface and its shared value types.

Concrete providers implement a single method, :meth:`LLMClient.complete`. Everything
the agents rely on — JSON-mode parsing, token accounting — is expressed on top of
that, so adding a provider stays cheap and every provider behaves identically from
the caller's point of view.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, ClassVar


class LLMError(RuntimeError):
    """Raised when a provider call fails or returns output we cannot use."""


class LLMConfigurationError(LLMError):
    """Raised when the LLM client cannot be built from the current settings.

    The most common cause is selecting a provider without supplying its API key.
    """


class Role(StrEnum):
    """The author of a message in a conversation."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass(frozen=True, slots=True)
class Message:
    """A single turn in a prompt."""

    role: Role
    content: str

    @classmethod
    def system(cls, content: str) -> Message:
        """A system/instruction message."""
        return cls(Role.SYSTEM, content)

    @classmethod
    def user(cls, content: str) -> Message:
        """A user message."""
        return cls(Role.USER, content)

    @classmethod
    def assistant(cls, content: str) -> Message:
        """An assistant/model message."""
        return cls(Role.ASSISTANT, content)


@dataclass(frozen=True, slots=True)
class TokenUsage:
    """Token counts for one call — the raw material of the cost metric."""

    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass(frozen=True, slots=True)
class LLMResponse:
    """A provider's reply, normalised across vendors."""

    text: str
    model: str
    usage: TokenUsage | None = None


class LLMClient(ABC):
    """Async interface every provider adapter implements.

    Subclasses implement :meth:`complete`; :meth:`generate_json` is provided here so
    structured-output parsing behaves identically across providers.
    """

    #: Stable identifier for the provider family (e.g. ``"gemini"``, ``"groq"``).
    provider: ClassVar[str]

    def __init__(self, *, model: str) -> None:
        self._model = model

    @property
    def model(self) -> str:
        """The concrete model name this client calls."""
        return self._model

    @abstractmethod
    async def complete(
        self,
        messages: Sequence[Message],
        *,
        temperature: float = 0.0,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Return the model's completion for ``messages``.

        When ``json_mode`` is set, the provider is instructed to emit a single JSON
        object. ``temperature`` defaults to ``0.0`` for the most reproducible runs the
        provider allows — reproducibility is a first-class requirement of the harness.
        """

    async def generate_json(
        self,
        messages: Sequence[Message],
        *,
        temperature: float = 0.0,
    ) -> Any:
        """Return the model's reply parsed from JSON.

        Raises :class:`LLMError` if the provider does not return valid JSON, so callers
        can treat a malformed structured response as a normal, handleable failure.
        """
        response = await self.complete(messages, temperature=temperature, json_mode=True)
        try:
            return json.loads(response.text)
        except json.JSONDecodeError as exc:
            raise LLMError(
                f"{self.provider} model {self.model} did not return valid JSON: {exc}"
            ) from exc
