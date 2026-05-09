"""
LLM provider registry.

Each provider is a thin wrapper around an upstream SDK. The base class enforces
uniform token/cost recording, duration tracking, and error envelope so the
centralized usage rollup in Settings stays accurate by construction.

DeepSeek is intentionally NOT in :data:`PROVIDERS` — it must never be
selected by the audit router. Tools that explicitly want a cheap
synthesis provider should use :func:`get_synthesis_provider`, which
reads ``settings.PROMPT_SYNTHESIS_PROVIDER`` and falls back across the
configured tooling chain.
"""
from .base import LLMProvider, ProviderResult
from .claude import ClaudeProvider
from .openai import OpenAIProvider
from .gemini import GeminiProvider
from .perplexity import PerplexityProvider
from .deepseek import DeepSeekProvider


PROVIDERS: dict[str, type[LLMProvider]] = {
    "claude": ClaudeProvider,
    "gpt4": OpenAIProvider,
    "gemini": GeminiProvider,
    "perplexity": PerplexityProvider,
}

# Tooling-only registry. Intentionally separate from ``PROVIDERS`` so a
# typo in audit code can't accidentally route a real audit through
# DeepSeek (which lacks citation metadata, web grounding, etc).
TOOLING_PROVIDERS: dict[str, type[LLMProvider]] = {
    "deepseek": DeepSeekProvider,
    "claude": ClaudeProvider,
    "gpt4": OpenAIProvider,
}


def get_provider(key: str) -> LLMProvider | None:
    """Instantiate a provider by audit-side key, or return None if not configured."""
    cls = PROVIDERS.get(key)
    if cls is None:
        return None
    instance = cls()
    return instance if instance.is_configured() else None


def get_synthesis_provider(key: str | None = None) -> LLMProvider | None:
    """Return a configured tooling provider for synthesis / auto-templating.

    Falls back across the configured choice -> deepseek -> claude -> gpt4
    so callers always get a usable provider when at least one key is set.
    Returns ``None`` only when no tooling provider has an API key — every
    caller must handle that case gracefully.
    """
    from django.conf import settings

    chain: list[str] = []
    chosen = key or getattr(settings, "PROMPT_SYNTHESIS_PROVIDER", "deepseek")
    chain.append(chosen)
    for fallback in ("deepseek", "claude", "gpt4"):
        if fallback not in chain:
            chain.append(fallback)
    for name in chain:
        cls = TOOLING_PROVIDERS.get(name)
        if cls is None:
            continue
        instance = cls()
        if instance.is_configured():
            return instance
    return None


__all__ = [
    "PROVIDERS",
    "TOOLING_PROVIDERS",
    "get_provider",
    "get_synthesis_provider",
    "LLMProvider",
    "ProviderResult",
    "ClaudeProvider",
    "OpenAIProvider",
    "GeminiProvider",
    "PerplexityProvider",
    "DeepSeekProvider",
]
