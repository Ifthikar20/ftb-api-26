"""Voice guard — score how close a draft sits to the brand's tone samples.

Average cosine similarity between draft chunks and the website's
:class:`apps.brand_vault.models.ToneSample` embeddings. Returns a score
0..1 plus a short note. Falls back to ``(0.5, "no tone samples available")``
when the website has no samples yet.
"""
from __future__ import annotations

import logging
from statistics import mean

from apps.brand_vault.models import ToneSample
from apps.brand_vault.services.embeddings import cosine_similarity, embed_text

logger = logging.getLogger("apps")

CHUNK_WORDS = 80


def _chunks(text: str, size: int = CHUNK_WORDS) -> list[str]:
    words = (text or "").split()
    if not words:
        return []
    return [" ".join(words[i : i + size]) for i in range(0, len(words), size)]


def score_voice(draft) -> tuple[float, str]:
    """Return ``(score, notes)`` for a :class:`ContentDraft`."""
    samples = list(
        ToneSample.objects.filter(website=draft.website)[:50]
    )
    if not samples:
        return 0.5, "no tone samples available"

    sample_embs: list[list[float]] = []
    for s in samples:
        emb = s.embedding if isinstance(s.embedding, list) and s.embedding else None
        if not emb:
            try:
                emb = embed_text(s.text or "")
            except Exception:
                emb = []
        if emb:
            sample_embs.append(emb)

    if not sample_embs:
        return 0.5, "tone samples lack embeddings"

    text = (draft.body_markdown or "").strip()
    chunks = _chunks(text)
    if not chunks:
        return 0.0, "draft body is empty"

    sims: list[float] = []
    for ch in chunks:
        try:
            ce = embed_text(ch)
        except Exception:
            continue
        if not ce:
            continue
        best = max(
            (cosine_similarity(ce, se) for se in sample_embs),
            default=0.0,
        )
        sims.append(best)

    if not sims:
        return 0.5, "could not embed draft chunks"

    score = max(0.0, min(1.0, mean(sims)))
    if score >= 0.75:
        note = "draft tone aligns closely with brand samples"
    elif score >= 0.5:
        note = "mostly aligned with brand voice; minor drift"
    else:
        note = "voice diverges from brand samples; consider revising tone"
    return score, note
