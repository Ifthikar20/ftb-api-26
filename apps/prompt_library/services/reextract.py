"""Backfill structured brand extraction onto prompt responses.

Older crawler rows (and any response captured before extraction was
wired into the crawl) were saved with the raw model text but never run
through HaikuExtractionService, so their competitors_mentioned /
mention_rank / sentiment are empty and the prompt-detail brand table
shows nothing. This module re-runs the extractor on exactly those rows.

A row is considered "un-extracted" when it succeeded, has response text,
and extraction_model is blank. Once re-extracted, extraction_model is
set (to the LLM model name, or "heuristic" when the LLM isn't
configured), so the row is never reprocessed and the backfill can't
loop.
"""
from __future__ import annotations

import logging

from django.conf import settings
from django.db.models import Q

from apps.llm_ranking.models import LLMRankingResult
from apps.llm_ranking.services.extraction_service import EXTRACTION_VERSION

logger = logging.getLogger("apps")


def _normalise(text: str) -> str:
    return " ".join((text or "").split()).lower()


def _stale_extraction_q() -> Q:
    """Rows whose extraction should be (re)run.

    Always: rows never extracted (extraction_model blank).
    When the LLM extractor is configured, also upgrade rows produced by an
    older extraction schema version (extraction_version != current). This
    covers heuristic-era rows and v1 LLM rows alike, and is loop-safe: a
    row is stamped with the current version after one pass regardless of
    whether the LLM or heuristic produced it, so it won't be re-run again.
    Gated on the key so a missing extractor can't churn on every load.
    """
    q = Q(extraction_model="")
    if getattr(settings, "ANTHROPIC_API_KEY", ""):
        q |= ~Q(extraction_version=EXTRACTION_VERSION)
    return q


def _prompt_match_q(prompt) -> Q:
    return (
        Q(source_prompt_id=prompt.id)
        | Q(prompt__icontains=prompt.text[:80])
        | Q(prompt__icontains=(prompt.template_text or "")[:80])
    )


def count_unextracted(website, prompt) -> int:
    """How many of this prompt's responses still need (re)extraction."""
    return len(unextracted_results(website, prompt))


def unextracted_results(website, prompt):
    """Successful, non-empty responses for this prompt that need structured
    extraction (never run, or stale per _stale_extraction_q)."""
    norm_text = _normalise(prompt.text)
    norm_template = _normalise(prompt.template_text or "")
    candidates = (
        LLMRankingResult.objects
        .filter(audit__website=website, query_succeeded=True)
        .filter(_stale_extraction_q())
        .exclude(response_text="")
        .filter(_prompt_match_q(prompt))
    )
    rows = []
    for r in candidates:
        rn = _normalise(r.prompt)
        if (
            r.source_prompt_id == prompt.id
            or rn == norm_text
            or (norm_template and rn == norm_template)
        ):
            rows.append(r)
    return rows


def _keywords_for(website) -> list[str]:
    out: list[str] = []
    name = getattr(website, "business_name", None) or website.name or ""
    if name:
        out.append(name)
    for t in (getattr(website, "topics", None) or []):
        if isinstance(t, str) and t.strip():
            out.append(t.strip())
    for c in (getattr(website, "competitors", None) or []):
        cname = c.get("name") if isinstance(c, dict) else (c if isinstance(c, str) else None)
        if cname and cname.strip():
            out.append(cname.strip())
    seen, deduped = set(), []
    for k in out:
        kl = k.lower()
        if kl not in seen:
            seen.add(kl)
            deduped.append(k)
    return deduped


def reextract_prompt(website, prompt) -> int:
    """Re-run extraction on every un-extracted response for this prompt.
    Returns the number of rows updated."""
    from apps.llm_ranking.services.extraction_service import HaikuExtractionService

    brand_name = getattr(website, "business_name", None) or website.name or "your brand"
    keywords = _keywords_for(website)

    rows = unextracted_results(website, prompt)
    updated = 0
    for r in rows:
        try:
            analysis = HaikuExtractionService.extract(
                response_text=r.response_text,
                brand_name=brand_name,
                keywords=keywords,
                user=getattr(website, "user", None),
                website=website,
                audit_id=str(r.audit_id),
            )
        except Exception as exc:
            logger.warning("Re-extraction failed for result %s: %s", r.id, exc)
            continue

        r.is_mentioned = analysis["is_mentioned"]
        r.mention_rank = analysis["mention_rank"]
        r.sentiment = analysis["sentiment"]
        r.confidence_score = analysis["confidence_score"]
        r.mention_context = analysis["mention_context"]
        r.is_linked = analysis.get("is_linked", False)
        r.competitors_mentioned = analysis.get("competitors_mentioned", [])
        r.primary_recommendation = analysis.get("primary_recommendation", "")
        r.citations = analysis.get("citations", [])
        # Guarantee the row is marked processed so it never loops, even if
        # the extractor returned the empty/blank-model shape.
        r.extraction_model = analysis.get("extraction_model") or "heuristic"
        r.extraction_version = analysis.get("extraction_version", "")
        r.save(update_fields=[
            "is_mentioned", "mention_rank", "sentiment", "confidence_score",
            "mention_context", "is_linked", "competitors_mentioned",
            "primary_recommendation", "citations", "extraction_model",
            "extraction_version", "updated_at",
        ])
        updated += 1

        # Re-dispatch citation extraction now that we have a fresh analysis.
        try:
            from apps.prompt_library.services.prompt_crawler import _dispatch_citations
            _dispatch_citations(r.id)
        except Exception:
            pass

    return updated
