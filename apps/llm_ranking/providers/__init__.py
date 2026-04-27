"""
LLM provider registry.

Each provider is a thin wrapper around an upstream SDK. The base class enforces
uniform token/cost recording, duration tracking, and error envelope so the
centralized usage rollup in Settings stays accurate by construction.
"""
from .base import LLMProvider, ProviderResult
from .claude import ClaudeProvider
from .openai import OpenAIProvider
from .gemini import GeminiProvider
from .perplexity import PerplexityProvider


PROVIDERS: dict[str, type[LLMProvider]] = {
    "claude": ClaudeProvider,
    "gpt4": OpenAIProvider,
    "gemini": GeminiProvider,
    "perplexity": PerplexityProvider,
}


def get_provider(key: str) -> LLMProvider | None:
    """Instantiate a provider by audit-side key, or return None if not configured."""
    cls = PROVIDERS.get(key)
    if cls is None:
        return None
    instance = cls()
    return instance if instance.is_configured() else None


__all__ = [
    "PROVIDERS",
    "get_provider",
    "LLMProvider",
    "ProviderResult",
    "ClaudeProvider",
    "OpenAIProvider",
    "GeminiProvider",
    "PerplexityProvider",
]
