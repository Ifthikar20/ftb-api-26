"""Tone sampler — pick representative chunks for brand voice modeling.

The sampler walks a website's KnowledgeChunks, prefers chunks tagged
``about`` / ``product`` / ``docs`` or longer paragraphs from the homepage,
and falls back to random sampling. Each accepted slice (80-300 words) is
persisted as a ToneSample, deduped on a sha256 of the text. Idempotent:
re-running on the same website only adds new samples.

These samples will feed Phase 4's voice guard — they are NOT facts,
they are tone-of-voice exemplars.
"""
from __future__ import annotations

import hashlib
import logging
import random
import re
from collections.abc import Iterable

from apps.brand_vault.models import ToneSample
from apps.brand_vault.services.embeddings import embed_text

logger = logging.getLogger("apps")


_PREFERRED_KINDS = ("homepage", "about", "product", "docs")
_MIN_WORDS = 80
_MAX_WORDS = 300


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def _slice_paragraphs(text: str) -> Iterable[str]:
    """Yield paragraph slices in the [_MIN_WORDS, _MAX_WORDS] range."""
    if not text:
        return
    parts = re.split(r"\n\s*\n", text.strip())
    for part in parts:
        words = part.split()
        if len(words) < _MIN_WORDS:
            continue
        if len(words) <= _MAX_WORDS:
            yield part.strip()
            continue
        # Window the long paragraph into max-sized slices.
        for start in range(0, len(words), _MAX_WORDS):
            window = words[start:start + _MAX_WORDS]
            if len(window) >= _MIN_WORDS:
                yield " ".join(window)


def _ranked_chunks(website_id: str):
    from apps.rag.models import KnowledgeChunk

    qs = (
        KnowledgeChunk.objects.filter(website_id=website_id)
        .select_related("source")
        .order_by("-token_count")
    )
    preferred, others = [], []
    for chunk in qs.iterator(chunk_size=200):
        kind = getattr(chunk.source, "kind", "") or ""
        if kind in _PREFERRED_KINDS:
            preferred.append(chunk)
        else:
            others.append(chunk)
    random.shuffle(others)
    return preferred + others


def sample_tone_from_chunks(website_id: str, target_count: int = 30) -> int:
    """Persist up to ``target_count`` new ToneSample rows for the website.

    Returns the number of new samples created. Skips text whose hash is
    already present (so the call is idempotent).
    """
    existing_hashes = set(
        ToneSample.objects.filter(website_id=website_id)
        .values_list("text_hash", flat=True),
    )
    created = 0
    for chunk in _ranked_chunks(website_id):
        if created >= target_count:
            break
        for slc in _slice_paragraphs(chunk.text or ""):
            if created >= target_count:
                break
            h = _hash(slc)
            if h in existing_hashes:
                continue
            try:
                emb = embed_text(slc)
            except Exception:  # pragma: no cover
                emb = None
            try:
                ToneSample.objects.create(
                    website_id=website_id,
                    source_chunk=chunk,
                    text=slc,
                    text_hash=h,
                    word_count=len(slc.split()),
                    embedding=emb,
                )
            except Exception as exc:  # pragma: no cover
                logger.warning("ToneSample create failed (%s): %s", website_id, exc)
                continue
            existing_hashes.add(h)
            created += 1
    return created
