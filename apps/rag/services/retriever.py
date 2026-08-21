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
import math
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlsplit

from django.db.models import Q
from django.utils import timezone

from apps.rag.models import KnowledgeChunk, KnowledgeSource
from apps.rag.services.embedder import cosine_similarity, embed_one

logger = logging.getLogger("apps")

DEFAULT_TOP_K = 5
DEFAULT_MIN_SCORE = 0.05

# Recency decay constant: weight = exp(-age_days / 65), a half-life of
# ~45 days. Applied to every source_app except brand_input — the
# user-curated corpus (and every legacy row, which carries the column
# default) is evergreen ground truth and keeps its raw cosine score.
RECENCY_DECAY_DAYS = 65.0

# Human header labels for sources without a real URL (synthetic schemes
# such as llmres:// or gsc://). Derived from the model choices so the
# admin and the prompt blocks always agree.
_SOURCE_APP_LABELS = dict(KnowledgeSource.SOURCE_APP_CHOICES)


@dataclass
class Hit:
    chunk_id: str
    source_id: str
    source_url: str
    source_kind: str
    section_label: str
    text: str
    score: float
    # Provenance (additive; defaults keep pre-existing constructors valid).
    source_app: str = KnowledgeSource.SOURCE_APP_BRAND_INPUT
    metadata: dict = field(default_factory=dict)
    recorded_at: datetime | None = None


def retrieve(
    *,
    user,
    website,
    query: str,
    top_k: int = DEFAULT_TOP_K,
    min_score: float = DEFAULT_MIN_SCORE,
    kinds: list[str] | None = None,
    source_ids: list[str] | None = None,
    source_apps: list[str] | None = None,
    since: datetime | None = None,
) -> list[Hit]:
    """Return the top ``top_k`` chunks for the query, scoped to (user, website).

    ``source_ids`` narrows retrieval to specific KnowledgeSource rows,
    powering the "test this source" affordance in the Brand Input drawer.
    ``source_apps`` narrows to the producing apps (values from
    ``KnowledgeSource.SOURCE_APP_CHOICES``). ``since`` keeps only chunks
    whose content time — ``recorded_at``, falling back to ``created_at``
    for legacy rows — is at or after the given datetime.

    Ranking: cosine similarity, recency-weighted by
    ``exp(-age_days / RECENCY_DECAY_DAYS)`` for every source_app except
    evergreen ``brand_input``, which keeps the raw cosine score.
    """
    if not query.strip():
        return []

    qs = (
        KnowledgeChunk.objects
        .filter(user=user, website=website)
        .select_related("source")
    )
    if kinds:
        qs = qs.filter(source__kind__in=kinds)
    if source_ids:
        qs = qs.filter(source_id__in=source_ids)
    if source_apps:
        qs = qs.filter(source__source_app__in=source_apps)
    if since is not None:
        qs = qs.filter(
            Q(recorded_at__gte=since)
            | Q(recorded_at__isnull=True, created_at__gte=since)
        )
    candidates = list(qs.only(
        "id", "embedding", "embedding_dim", "text", "section_label",
        "metadata", "recorded_at", "created_at",
        "source__id", "source__url", "source__kind", "source__source_app",
    ))
    if not candidates:
        return []

    query_vec, _model, _dim = embed_one(
        query, user=user, website=website,
        metadata={"role": "retrieval_query"},
    )
    if not query_vec:
        return []

    now = timezone.now()
    scored: list[tuple[float, KnowledgeChunk]] = []
    for chunk in candidates:
        if not chunk.embedding or len(chunk.embedding) != len(query_vec):
            # Mixing embedding dimensions across model upgrades: skip
            # mismatched ones rather than corrupting the ranking.
            continue
        score = cosine_similarity(query_vec, chunk.embedding)
        score *= _recency_weight(chunk, now)
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
            source_app=chunk.source.source_app,
            metadata=chunk.metadata or {},
            recorded_at=chunk.recorded_at,
        ))
    return hits


def _recency_weight(chunk: KnowledgeChunk, now: datetime) -> float:
    """Exponential recency decay; 1.0 for evergreen brand_input.

    Age is measured from ``recorded_at`` (content time), falling back to
    ``created_at`` (ingest time) for legacy rows. Future timestamps clamp
    to zero age so nothing scores above its raw cosine.
    """
    if chunk.source.source_app == KnowledgeSource.SOURCE_APP_BRAND_INPUT:
        return 1.0
    stamp = chunk.recorded_at or chunk.created_at
    if stamp is None:  # pragma: no cover — created_at is auto-set
        return 1.0
    age_days = max((now - stamp).total_seconds(), 0.0) / 86400.0
    return math.exp(-age_days / RECENCY_DECAY_DAYS)


def _hit_origin(hit: Hit) -> str:
    """Header origin: URL fragment for real pages, source_app label otherwise.

    Synthetic schemes (``llmres://``, ``gsc://``, ``audit://``...) mean
    nothing to the model reading the prompt, so those hits are labeled by
    what produced them instead.
    """
    scheme = urlsplit(hit.source_url).scheme.lower()
    if scheme in ("http", "https"):
        return hit.source_url[:80]
    return _SOURCE_APP_LABELS.get(
        hit.source_app,
        (hit.source_app or "knowledge").replace("_", " ").capitalize(),
    )


def retrieve_context_block(
    *,
    user,
    website,
    query: str,
    top_k: int = DEFAULT_TOP_K,
    max_chars: int = 3000,
    kinds: list[str] | None = None,
    source_apps: list[str] | None = None,
    since: datetime | None = None,
) -> str:
    """Return retrieved chunks formatted as a system-prompt-ready block."""
    hits = retrieve(
        user=user, website=website, query=query,
        top_k=top_k, kinds=kinds,
        source_apps=source_apps, since=since,
    )
    if not hits:
        return ""
    lines = ["=== KNOWLEDGE BASE ==="]
    used = len(lines[0]) + 1
    for hit in hits:
        header = f"\n--- {hit.section_label or hit.source_kind} ({_hit_origin(hit)}) ---"
        body = hit.text.strip()
        block = f"{header}\n{body}"
        if used + len(block) > max_chars:
            break
        lines.append(block)
        used += len(block) + 1
    return "\n".join(lines)
