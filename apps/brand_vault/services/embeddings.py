"""Thin wrapper around apps.rag's embedder.

Delegates to ``apps.rag.services.embedder.embed_one`` so the brand_vault
fact retrieval path uses the same vector space as the RAG knowledge base.
If the rag module isn't importable for some reason, falls back to a
simple deterministic hash-based 32-dim embedding so tests still work.
"""
from __future__ import annotations

import hashlib
import math
import re

FALLBACK_DIM = 32


def embed_text(text: str) -> list[float]:
    """Return an embedding vector for ``text``.

    Always returns a list[float]; falls back to a deterministic hash
    embedding if the OpenAI-backed rag embedder is unavailable.
    """
    text = (text or "").strip()
    if not text:
        return []
    try:
        from apps.rag.services.embedder import embed_one
        vec, _model, _dim = embed_one(text)
        if vec:
            return list(vec)
    except Exception:
        pass
    return _hash_embed(text)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = na = nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na == 0 or nb == 0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))


def _hash_embed(text: str) -> list[float]:
    tokens = [t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) > 1]
    if not tokens:
        return [0.0] * FALLBACK_DIM
    vec = [0.0] * FALLBACK_DIM
    for tok in tokens:
        h = hashlib.sha1(tok.encode("utf-8")).digest()
        bucket = int.from_bytes(h[:4], "big") % FALLBACK_DIM
        vec[bucket] += 1.0
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0:
        return vec
    return [v / norm for v in vec]
