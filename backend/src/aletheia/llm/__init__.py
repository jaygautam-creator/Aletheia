"""Provider-agnostic LLM client.

Aletheia must never be locked to one model vendor: the evaluation harness needs to
swap models for fair comparison, and the project runs on whichever free tier a user
holds a key for. Every agent therefore talks to an :class:`~aletheia.llm.base.LLMClient`
— a thin async interface — and the concrete provider is chosen at the edge by
:func:`~aletheia.llm.factory.build_llm_client`.
"""

from aletheia.llm.base import (
    LLMClient,
    LLMConfigurationError,
    LLMError,
    LLMResponse,
    Message,
    Role,
    TokenUsage,
)
from aletheia.llm.factory import DEFAULT_MODELS, build_llm_client
from aletheia.llm.fake import FakeLLMClient

__all__ = [
    "DEFAULT_MODELS",
    "FakeLLMClient",
    "LLMClient",
    "LLMConfigurationError",
    "LLMError",
    "LLMResponse",
    "Message",
    "Role",
    "TokenUsage",
    "build_llm_client",
]
