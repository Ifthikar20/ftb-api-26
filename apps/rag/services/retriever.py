"""
Retrieval over the per-user knowledge base.

Top-k cosine similarity, scoped to (user, website). With per-website
corpora bounded in the low thousands of chunks, brute-force scoring
in Python is comfortably under 100ms.

When the corpus grows larger, swap the candidate selection for a
pgvector / ANN index without changing the call sites.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from apps.rag.models import KnowledgeChunk
from apps.rag.services.embedder import cosine_similarity, embed_one

logger = logging.getLogger("apps")

DEFAULT_TOP_K = 5
DEFAULT_MIN_SCORE = 0.05


@dataclass
class Hit:
    chunk_id: str
    source_id: str
    source_url: str
    source_kind: str
    section_label: str
    text: str
    score: float


def retrieve(
    *,
    user,
    website,
    query: str,
    top_k: int = DEFAULT_TOP_K,
    min_score: float = DEFAULT_MIN_SCORE,
    kinds: list[str] | None = None,
) -> list[Hit]:
    """Return the top ``top_k`` chunks for the query, scoped to (user, website)."""
    if not query.strip():
        return []

    qs = (
        KnowledgeChunk.objects
        .filter(user=user, website=website)
        .select_related("source")
    )
    if kinds:
        qs = qs.filter(source__kind__in=kinds)
    candidates = list(qs.only(
        "id", "embedding", "embedding_dim", "text", "section_label",
        "source__id", "source__url", "source__kind",
    ))
    if not candidates:
        return []

    query_vec, _model, _dim = embed_one(
        query, user=user, website=website,
        metadata={"role": "retrieval_query"},
    )
    if not query_vec:
        return []

    scored: list[tuple[float, KnowledgeChunk]] = []
    for chunk in candidates:
        if not chunk.embedding or len(chunk.embedding) != len(query_vec):
            # Mixing embedding dimensions across model upgrades: skip
            # mismatched ones rather than corrupting the ranking.
            continue
        score = cosine_similarity(query_vec, chunk.embedding)
        if score >= min_score:
            scored.append((score, chunk))

    scored.sort(key=lambda t: t[0], reverse=True)
    hits: list[Hit] = []
    for score, chunk in scored[:top_k]:
        hits.append(Hit(
            chunk_id=str(chunk.id),
            source_id=str(chunk.source_id),
            source_url=chunk.source.url,
            source_kind=chunk.source.kind,
            section_label=chunk.section_label,
            text=chunk.text,
            score=float(score),
        ))
    return hits


def retrieve_context_block(
    *,
    user,
    website,
    query: str,
    top_k: int = DEFAULT_TOP_K,
    max_chars: int = 3000,
    kinds: list[str] | None = None,
) -> str:
    """Return retrieved chunks formatted as a system-prompt-ready block."""
    hits = retrieve(
        user=user, website=website, query=query,
        top_k=top_k, kinds=kinds,
    )
    if not hits:
        return ""
    lines = ["=== KNOWLEDGE BASE ==="]
    used = len(lines[0]) + 1
    for hit in hits:
        header = f"\n--- {hit.section_label or hit.source_kind} ({hit.source_url[:80]}) ---"
        body = hit.text.strip()
        block = f"{header}\n{body}"
        if used + len(block) > max_chars:
            break
        lines.append(block)
        used += len(block) + 1
    return "\n".join(lines)
