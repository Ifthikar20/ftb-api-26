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
from .deepseek import DeepSeekProvider
from .gemini import GeminiProvider
from .grok import GrokProvider
from .openai import OpenAIProvider
from .perplexity import PerplexityProvider

PROVIDERS: dict[str, type[LLMProvider]] = {
    "claude": ClaudeProvider,
    "gpt4": OpenAIProvider,
    "gemini": GeminiProvider,
    "perplexity": PerplexityProvider,
    "grok": GrokProvider,
}


# Selectable model variants per provider. Order matters — the first entry
# in each list is the default when only a provider key is supplied. Each
# variant tuple is (label, model_id, is_default).
#
# Adding a model here exposes it in the Model Test picker. Removing one
# does not break historical runs (results store the model_id verbatim).
MODEL_VARIANTS: dict[str, list[tuple[str, str, bool]]] = {
    "claude": [
        ("Sonnet 4.5", "claude-sonnet-4-5-20250929", False),
        ("Sonnet 4",   "claude-sonnet-4-20250514",   True),
        ("Opus 4.1",   "claude-opus-4-1-20250805",   False),
        ("Haiku 4.5",  "claude-haiku-4-5-20251001",  False),
    ],
    "gpt4": [
        ("GPT-4o",      "gpt-4o",       False),
        ("GPT-4o mini", "gpt-4o-mini",  True),
        ("GPT-4 Turbo", "gpt-4-turbo",  False),
    ],
    "gemini": [
        ("Gemini 1.5 Pro",   "gemini-1.5-pro",   False),
        ("Gemini 1.5 Flash", "gemini-1.5-flash", True),
        ("Gemini 2.0 Flash", "gemini-2.0-flash", False),
    ],
    "perplexity": [
        ("Sonar Small (web)", "llama-3.1-sonar-small-128k-online", True),
        ("Sonar Large (web)", "llama-3.1-sonar-large-128k-online", False),
    ],
    "grok": [
        ("Grok 4", "grok-4", True),
        ("Grok 3", "grok-3", False),
    ],
    # DeepSeek is excluded from the main audit registry (PROVIDERS) but
    # surfaced in the Model Test picker because it's a cheap, useful
    # baseline for "did the model mention us" probes. The variants
    # registry, list_model_variants(), and get_provider_for_variant()
    # all consult TOOLING_PROVIDERS for these so the audit router
    # remains unaffected.
    "deepseek": [
        ("DeepSeek Chat",     "deepseek-chat",     True),
        ("DeepSeek Reasoner", "deepseek-reasoner", False),
    ],
}


def list_model_variants() -> list[dict]:
    """Return a flat list of variants for the picker UI.

    Each entry includes the provider key, the canonical variant id (used
    as the wire-format choice in Model Test runs), the model id sent to
    the SDK, a friendly label, and whether the underlying provider is
    configured. Variants are excluded when the provider class isn't in
    either PROVIDERS or TOOLING_PROVIDERS (defensive — should not
    happen). DeepSeek is sourced from TOOLING_PROVIDERS so it appears
    in Model Test but stays out of the main audit router.
    """
    from django.conf import settings
    out: list[dict] = []
    for provider_key, variants in MODEL_VARIANTS.items():
        cls = PROVIDERS.get(provider_key) or TOOLING_PROVIDERS.get(provider_key)
        if cls is None:
            continue
        configured = bool(getattr(settings, cls.api_key_setting, ""))
        for label, model_id, is_default in variants:
            out.append({
                "id": f"{provider_key}:{model_id}",
                "provider": provider_key,
                "model_id": model_id,
                "label": label,
                "is_default": is_default,
                "configured": configured,
            })
    return out


def parse_variant(variant_id: str) -> tuple[str, str] | None:
    """Split `"<provider>:<model_id>"` into (provider, model_id).

    Returns None when the variant is malformed or references a provider
    that no longer exists. The caller should treat None as an unknown
    variant and surface a clear error to the user. Accepts any provider
    that's in PROVIDERS *or* TOOLING_PROVIDERS so Model Test can route
    to DeepSeek (which is tooling-only).
    """
    if not variant_id or ":" not in variant_id:
        return None
    provider, model_id = variant_id.split(":", 1)
    provider = provider.strip().lower()
    model_id = model_id.strip()
    if not provider or not model_id:
        return None
    if provider not in PROVIDERS and provider not in TOOLING_PROVIDERS:
        return None
    return provider, model_id


def default_variant_for(provider_key: str) -> str | None:
    """Return the wire-format id of the default variant for a provider."""
    variants = MODEL_VARIANTS.get(provider_key) or []
    for _label, model_id, is_default in variants:
        if is_default:
            return f"{provider_key}:{model_id}"
    if variants:
        return f"{provider_key}:{variants[0][1]}"
    return None


def get_provider_for_variant(variant_id: str) -> LLMProvider | None:
    """Instantiate a configured provider bound to the variant's model id.

    Mutates the instance's `.model` so the upstream SDK call routes to
    the requested variant. Returns None when the provider is unknown,
    the variant is malformed, or the API key isn't configured. Looks
    up the class in PROVIDERS first, then TOOLING_PROVIDERS, so Model
    Test can dispatch DeepSeek without polluting the audit router.
    """
    parsed = parse_variant(variant_id)
    if parsed is None:
        return None
    provider_key, model_id = parsed
    cls = PROVIDERS.get(provider_key) or TOOLING_PROVIDERS.get(provider_key)
    if cls is None:
        return None
    instance = cls()
    if not instance.is_configured():
        return None
    instance.model = model_id
    return instance

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
    "GrokProvider",
    "DeepSeekProvider",
]
