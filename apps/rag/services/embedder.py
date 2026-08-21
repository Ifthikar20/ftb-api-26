"""
Embedding service for the RAG knowledge base.

Primary: OpenAI ``text-embedding-3-small`` (1536 dim) via the OpenAI SDK
that's already a project dependency. Cheap (~$0.02 per 1M tokens) and
strong on English text.

Fallback: a deterministic 256-dim hash-based embedder. This isn't a real
semantic model — it's intended for tests and for environments without an
API key. Cosine similarity between hashed embeddings still ranks
identical strings above unrelated ones, which is enough for unit tests
to exercise the retrieval path.

We log usage via ``core.ai_tracking.record_usage`` so embedding spend
shows up alongside provider + extraction spend in the same dashboard.
"""
from __future__ import annotations

import hashlib
import logging
import math
import re

from django.conf import settings

logger = logging.getLogger("apps")

OPENAI_MODEL = "text-embedding-3-small"
OPENAI_DIM = 1536
FALLBACK_MODEL = "hash-256"
FALLBACK_DIM = 256

# Soft input limit per chunk — well below the ~8K token model cap so
# even pathological inputs don't blow up the API call.
_MAX_INPUT_CHARS = 8000


def embed_texts(
    texts: list[str],
    *,
    user=None,
    website=None,
    metadata: dict | None = None,
) -> tuple[list[list[float]], str, int]:
    """Embed a batch of strings.

    Returns ``(vectors, model_name, dim)``. Falls back to the
    deterministic hash embedder when no OpenAI key is configured, the
    account's monthly AI allowance is spent, or the upstream call fails —
    callers don't need to special-case absence.
    """
    if not texts:
        return [], "", 0

    cleaned = [(_truncate(t) or " ") for t in texts]
    api_key = getattr(settings, "OPENAI_API_KEY", "") or ""

    # Same spend wall as every chat-model call. Embeddings are cheap but
    # they are still metered spend; an exhausted allowance degrades to
    # the free hash embedder instead of quietly billing past the cap.
    if api_key and user is not None:
        from core.llm import allowance_denial
        denial = allowance_denial(user)
        if denial:
            logger.info("Embedding request denied by spend wall: %s", denial)
            api_key = ""

    if api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            resp = client.embeddings.create(model=OPENAI_MODEL, input=cleaned)
            vectors = [d.embedding for d in resp.data]
            try:
                from core.ai_tracking import record_usage
                usage = getattr(resp, "usage", None)
                tokens_in = getattr(usage, "prompt_tokens", 0) if usage else 0
                record_usage(
                    module="rag",
                    model_name=OPENAI_MODEL,
                    input_tokens=tokens_in,
                    output_tokens=0,
                    user=user,
                    website=website,
                    metadata={"role": "embedding", **(metadata or {})},
                )
            except Exception:
                pass
            return vectors, OPENAI_MODEL, OPENAI_DIM
        except Exception as exc:
            logger.warning("OpenAI embedding failed, falling back to hash embedder: %s", exc)

    # Deterministic fallback.
    return [_hash_embed(t) for t in cleaned], FALLBACK_MODEL, FALLBACK_DIM


def embed_one(text: str, **kw) -> tuple[list[float], str, int]:
    """Convenience wrapper for a single string."""
    vectors, model, dim = embed_texts([text], **kw)
    return (vectors[0] if vectors else []), model, dim


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two equal-length vectors. 0 for empty."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b, strict=False):
        dot += x * y
        na += x * x
        nb += y * y
    if na == 0 or nb == 0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))


def _truncate(text: str) -> str:
    text = (text or "").strip()
    if len(text) > _MAX_INPUT_CHARS:
        return text[:_MAX_INPUT_CHARS]
    return text


def _hash_embed(text: str) -> list[float]:
    """
    Deterministic hashed bag-of-words embedding.

    Tokens are lowercased, stripped of punctuation, and each one
    contributes ``+1`` to the bucket selected by SHA1(token) mod dim.
    The vector is then L2-normalised so cosine similarity is meaningful.

    This is NOT semantic — it gives near-zero similarity between
    paraphrases. It's only here so the retrieval path is exercisable in
    tests and dev environments without an OpenAI key.
    """
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
