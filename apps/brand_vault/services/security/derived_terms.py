"""Derive extra search terms from the client's ingested brand material.

The Monitoring config's brand terms tell the scans what the brand is
called; the knowledge base captured on the Brand Input page tells us what
the brand makes and says — product names, feature names, campaign titles.
This module mines KnowledgeSource titles for distinctive phrases so the
Reddit/X/Trends searches also catch discussions that never name the brand
directly.

Deliberately heuristic and deterministic: no LLM call, no API key, stable
under tests. A bad derived term costs one wasted search whose results the
judge then discards, so extraction only ever widens coverage.
"""
from __future__ import annotations

import re

from apps.rag.models import KnowledgeSource

# Segments matching these (case-insensitive, exact) are navigation or
# boilerplate, not searchable brand vocabulary.
_GENERIC_SEGMENTS = frozenset({
    "home", "homepage", "about", "about us", "blog", "docs",
    "documentation", "pricing", "contact", "contact us", "faq", "faqs",
    "help", "support", "help center", "privacy policy", "privacy",
    "terms", "terms of service", "terms and conditions", "login",
    "log in", "sign in", "sign up", "welcome", "overview",
    "introduction", "getting started", "refund policy", "careers",
    "news", "resources", "features", "products", "solutions",
    "official site", "official website",
})

# Title separators commonly used by CMSes: "Acme — Pricing", "Acme | Blog".
_SEPARATORS = re.compile(r"\s*(?:\||—|–|·|:|»|/|\s-\s)\s*")

_MAX_SEGMENT_WORDS = 6
_MIN_SEGMENT_CHARS = 3

DEFAULT_LIMIT = 5


def derived_search_terms(
    website,
    *,
    exclude: list[str] | tuple[str, ...] = (),
    limit: int = DEFAULT_LIMIT,
) -> list[str]:
    """Distinctive phrases mined from the website's knowledge base.

    Reads the titles of the website's ready KnowledgeSources (the corpus
    is shared across the website's users, so no user filter),
    splits them on CMS separators, and keeps short, non-generic segments
    that are not already in ``exclude`` (typically the brand terms).
    Ordered by source recency, deduped case-insensitively, capped at
    ``limit``. Returns [] on any error — search-term derivation must never
    break a scan.
    """
    if limit <= 0:
        return []
    try:
        titles = list(
            KnowledgeSource.objects.filter(
                website=website,
                status=KnowledgeSource.STATUS_READY,
            )
            .exclude(kind=KnowledgeSource.KIND_AUDIT_CONTEXT)
            .exclude(title="")
            .order_by("-last_ingested_at", "-created_at")
            .values_list("title", flat=True)[:100],
        )
    except Exception:
        return []

    excluded = {str(t).strip().lower() for t in exclude if str(t).strip()}
    seen: set[str] = set()
    out: list[str] = []
    for title in titles:
        for segment in _SEPARATORS.split(title or ""):
            term = _clean_segment(segment)
            if not term:
                continue
            key = term.lower()
            if key in seen or key in excluded or key in _GENERIC_SEGMENTS:
                continue
            seen.add(key)
            out.append(term)
            if len(out) >= limit:
                return out
    return out


def _clean_segment(segment: str) -> str:
    term = " ".join((segment or "").split()).strip(" \t\"'.,;!?()[]")
    if len(term) < _MIN_SEGMENT_CHARS:
        return ""
    if len(term.split()) > _MAX_SEGMENT_WORDS:
        return ""
    # Pure numbers or symbols are never useful queries.
    if not re.search(r"[a-zA-Z]", term):
        return ""
    return term
