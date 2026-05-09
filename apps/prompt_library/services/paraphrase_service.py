"""Generate prompt paraphrases via the existing Anthropic provider.

Stored as :class:`PromptVariation` rows. Embeddings are populated when
the rag embedder is available; otherwise the variation is saved without
an embedding and the dedup service falls back to a trigram heuristic.
"""
from __future__ import annotations

import json
import logging
import re

from apps.prompt_library.models import Prompt, PromptVariation
from apps.prompt_library.services._hash import text_hash

logger = logging.getLogger("apps")

META_PROMPT = (
    "Rewrite the following question into {n} natural-language paraphrases "
    "that a real user might type. Preserve the original intent. Return a "
    "JSON list of strings only.\n\nQuestion: {text}"
)


def _parse_list(text: str) -> list[str]:
    if not text:
        return []
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        return []
    try:
        items = json.loads(match.group())
    except Exception:
        return []
    return [str(x).strip() for x in items if isinstance(x, (str, int, float)) and str(x).strip()]


def _embed(text: str) -> tuple[list[float] | None, str]:
    try:
        from apps.rag.services import embedder  # type: ignore
    except Exception:  # pragma: no cover
        return None, ""
    fn = (
        getattr(embedder, "embed_text", None)
        or getattr(embedder, "embed", None)
        or getattr(embedder, "get_embedding", None)
    )
    if fn is None:
        return None, ""
    try:
        vec = fn(text)
        return (list(vec) if vec is not None else None), getattr(embedder, "MODEL", "")
    except Exception as exc:  # pragma: no cover
        logger.warning("paraphrase embedder failed: %s", exc)
        return None, ""


def generate_paraphrases(prompt: Prompt, n: int = 3) -> list[PromptVariation]:
    """Generate up to ``n`` paraphrases of ``prompt`` and persist them."""
    try:
        from apps.llm_ranking.providers import (
            get_provider,
            get_synthesis_provider,
        )
    except Exception as exc:  # pragma: no cover
        logger.warning("paraphrase: provider registry unavailable: %s", exc)
        return []

    # Prefer the configured synthesis provider (DeepSeek when available)
    # for cheap paraphrasing; fall back to the audit-tier providers when
    # no tooling key is configured.
    provider = None
    try:
        provider = get_synthesis_provider()
    except Exception:
        provider = None
    if provider is None:
        for name in ("claude", "gpt4"):
            try:
                provider = get_provider(name)
                if provider is not None:
                    break
            except Exception:
                continue
    if provider is None:
        logger.warning("paraphrase: no provider configured")
        return []

    body = META_PROMPT.format(n=n, text=prompt.text)
    try:
        result = provider.query(body, "", user=None, website=None, audit_id="prompt_library_paraphrase")
        text = getattr(result, "text", "") or ""
    except Exception as exc:
        logger.warning("paraphrase provider failed: %s", exc)
        return []

    variations: list[PromptVariation] = []
    for cand in _parse_list(text)[:n]:
        h = text_hash(cand)
        if PromptVariation.objects.filter(parent_prompt=prompt, text_hash=h).exists():
            continue
        vec, model = _embed(cand)
        v = PromptVariation.objects.create(
            parent_prompt=prompt,
            text=cand,
            text_hash=h,
            embedding=vec,
            embedding_model=model,
        )
        variations.append(v)
    return variations
