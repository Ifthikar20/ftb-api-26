"""Near-duplicate detection for prompt mining.

Uses cosine similarity over the existing rag embedder. Falls back to a
trigram-overlap heuristic when the embedder cannot be loaded (e.g. when
``OPENAI_API_KEY`` is not configured in test environments).
"""
from __future__ import annotations

import logging
import math
from collections.abc import Iterable

logger = logging.getLogger("apps")

SIMILARITY_THRESHOLD = 0.92


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _trigrams(text: str) -> set[str]:
    t = (text or "").lower().strip()
    if len(t) < 3:
        return {t}
    return {t[i : i + 3] for i in range(len(t) - 2)}


def _trigram_jaccard(a: str, b: str) -> float:
    ta, tb = _trigrams(a), _trigrams(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _embed(text: str) -> list[float] | None:
    try:
        from apps.rag.services import embedder  # type: ignore
    except Exception:  # pragma: no cover
        return None
    fn = (
        getattr(embedder, "embed_text", None)
        or getattr(embedder, "embed", None)
        or getattr(embedder, "get_embedding", None)
    )
    if fn is None:
        return None
    try:
        vec = fn(text)
        if vec is None:
            return None
        return list(vec)
    except Exception as exc:  # pragma: no cover
        logger.warning("dedup embedder failed: %s", exc)
        return None


def is_near_duplicate(
    candidate_text: str,
    industry,
    threshold: float = SIMILARITY_THRESHOLD,
) -> bool:
    """Return ``True`` if ``candidate_text`` is a near-duplicate of an
    existing prompt or variation in the same industry."""
    from apps.prompt_library.models import Prompt, PromptVariation

    cand_vec = _embed(candidate_text)

    existing_prompts = Prompt.objects.filter(industry=industry, is_active=True)
    if cand_vec is None:
        # Fallback heuristic — pure-Python trigram comparison.
        for p in existing_prompts.only("text"):
            if _trigram_jaccard(candidate_text, p.text) >= threshold:
                return True
        return False

    variations = PromptVariation.objects.filter(
        parent_prompt__industry=industry, embedding__isnull=False
    ).only("embedding", "text")
    for v in variations:
        if _cosine(cand_vec, v.embedding or []) >= threshold:
            return True
    return False


def filter_unique(
    candidates: Iterable[str], industry, threshold: float = SIMILARITY_THRESHOLD
) -> list[str]:
    """Return the subset of ``candidates`` that are not near-duplicates."""
    out: list[str] = []
    for text in candidates:
        if not is_near_duplicate(text, industry, threshold=threshold):
            out.append(text)
    return out
