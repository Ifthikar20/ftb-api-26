"""
Per-prompt crawler.

Given a (website, Prompt) pair, run the prompt across every configured
LLM provider and capture:

* The model's full response (stored on an ad-hoc LLMRankingAudit/Result
  row so the detail-page aggregation picks it up alongside any
  full-audit data).
* A list of fan-out sub-queries (PromptFanout rows). When Claude is
  available we ask it to decompose the prompt into 4-8 buyer-intent
  sub-queries; otherwise a deterministic heuristic templates them
  from the prompt's keywords so the UI still has something to show.

The whole thing is invoked synchronously from a Celery task; views
fire-and-forget via ``.delay()``. Failures on a single provider don't
fail the whole crawl — we record what we got.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from django.utils import timezone

from apps.llm_ranking.models import LLMRankingAudit, LLMRankingResult
from apps.llm_ranking.providers import (
    PROVIDERS,
    list_model_variants,
)
from apps.prompt_library.models import (
    Prompt,
    PromptCrawlRun,
    PromptFanout,
)
from apps.websites.models import Website

logger = logging.getLogger(__name__)


FANOUT_MIN = 4
FANOUT_MAX = 8


@dataclass
class CrawlOutcome:
    fanouts: list[str]
    responses: int
    errors: list[str]


def _llm_fanout(prompt_text: str, brand_name: str) -> list[str]:
    """Ask Claude to decompose the prompt into buyer-intent sub-queries.

    Falls back to ``_heuristic_fanout`` if Claude isn't configured or
    the call fails — we never raise from here so the crawler keeps
    going.
    """
    try:
        # Lazy import — if Anthropic isn't installed or the key isn't
        # set, the provider raises on instantiation and we drop to
        # the heuristic path below.
        from apps.llm_ranking.providers.claude import ClaudeProvider
        prov = ClaudeProvider()
    except Exception:
        return _heuristic_fanout(prompt_text)

    system = (
        "You break a buyer-intent prompt into 4-8 short sub-queries an "
        "AI search engine would run in parallel to gather context. "
        "Return only a JSON array of strings, no commentary."
    )
    user = f"Brand: {brand_name}\nPrompt: {prompt_text}"
    try:
        resp = prov.query(user, system_prompt=system)
    except Exception as exc:
        logger.warning("Fanout LLM call failed: %s", exc)
        return _heuristic_fanout(prompt_text)

    text = getattr(resp, "text", None) or str(resp)
    # Pull the first JSON array out of the response.
    match = re.search(r"\[[^\]]+\]", text or "", re.DOTALL)
    if not match:
        return _heuristic_fanout(prompt_text)
    try:
        items = json.loads(match.group())
    except json.JSONDecodeError:
        return _heuristic_fanout(prompt_text)
    cleaned = [str(x).strip() for x in items if isinstance(x, str | int | float) and str(x).strip()]
    return cleaned[:FANOUT_MAX] or _heuristic_fanout(prompt_text)


def _heuristic_fanout(prompt_text: str) -> list[str]:
    """Template a handful of sub-queries from the prompt's keywords.

    Crude but deterministic, and the page is rarely empty even when
    the LLM path is unavailable.
    """
    text = (prompt_text or "").strip()
    if not text:
        return []
    # Pull the noun-ish phrases by stripping question words + trailing
    # punctuation. Good enough for typical buyer-intent prompts.
    stripped = re.sub(r"^(which|what|how|where|when|why|who|find|recommend|show me|list|compare|evaluate)\s+", "", text, flags=re.I)
    stripped = re.sub(r"[?.!]+$", "", stripped).strip()
    if not stripped:
        return []
    base = stripped[:120]
    return [
        f"best {base}",
        f"top alternatives to {base}",
        f"{base} reviews and ratings",
        f"{base} vs competitors",
        f"how to choose {base}",
        f"pricing for {base}",
    ]


def _website_keywords(website: Website) -> list[str]:
    """Keywords the extractor uses to recognise the brand. Combines the
    business name, configured topics, and competitor names so the LLM
    extractor has enough context to label mentions."""
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
    # De-dupe, preserve order.
    seen, deduped = set(), []
    for k in out:
        kl = k.lower()
        if kl not in seen:
            seen.add(kl)
            deduped.append(k)
    return deduped


def _extract_brands(*, response_text, website, brand_name, keywords, audit_id) -> dict:
    """Run the same structured extraction the full audit uses so the
    crawl captures the brand, its rank/sentiment, and every competitor
    named in the response. Falls back to an empty analysis when there's
    no text or the extractor errors."""
    if not (response_text or "").strip():
        from apps.llm_ranking.services.extraction_service import HaikuExtractionService
        return HaikuExtractionService._empty_result()
    try:
        from apps.llm_ranking.services.extraction_service import HaikuExtractionService
        return HaikuExtractionService.extract(
            response_text=response_text,
            brand_name=brand_name,
            keywords=keywords,
            user=getattr(website, "user", None),
            website=website,
            audit_id=audit_id,
        )
    except Exception as exc:
        logger.warning("Crawl extraction failed: %s", exc)
        from apps.llm_ranking.services.extraction_service import HaikuExtractionService
        return HaikuExtractionService._empty_result()


def _dispatch_citations(result_id) -> None:
    """Kick off citation extraction so the Top Domains table populates.
    Mirrors the main audit flow; failures are non-fatal."""
    from django.conf import settings as _settings
    if not getattr(_settings, "CITATION_EXTRACTION_ENABLED", True):
        return
    try:
        from apps.citations.tasks import extract_citations_for_result
        extract_citations_for_result.delay(str(result_id))
    except Exception as exc:  # pragma: no cover
        logger.debug("citation dispatch failed for %s: %s", result_id, exc)


def crawl_prompt(website: Website, prompt: Prompt) -> CrawlOutcome:
    """Run a prompt across every configured provider and persist the
    fanout + responses. Returns a small outcome summary used by the
    Celery task to update the PromptCrawlRun row.
    """
    run = PromptCrawlRun.objects.create(
        website=website,
        prompt=prompt,
        status=PromptCrawlRun.STATUS_RUNNING,
        started_at=timezone.now(),
    )

    fanouts: list[str] = []
    errors: list[str] = []
    responses_logged = 0

    brand_name = getattr(website, "business_name", None) or website.name or "your brand"
    keywords = _website_keywords(website)
    fanouts = _llm_fanout(prompt.text or prompt.template_text or "", brand_name)

    # Persist fan-out rows. Bulk create with ignore_conflicts so a
    # re-crawl doesn't double-write.
    PromptFanout.objects.bulk_create(
        [
            PromptFanout(
                website=website,
                prompt=prompt,
                text=q,
                source=PromptFanout.SOURCE_CRAWLER,
                confidence=0.7,
            )
            for q in fanouts
        ],
        ignore_conflicts=True,
    )

    # Run the original prompt against each configured provider and
    # log the responses as LLMRankingResult rows on a synthetic audit.
    # The Prompt-detail page reads from LLMRankingResult, so this is
    # what makes the visibility/sentiment numbers light up.
    audit = LLMRankingAudit.objects.create(
        website=website,
        # Audit rows require a created_by; the crawl is run on behalf of
        # the website's owner regardless of which user kicked the scan.
        created_by=website.user,
        business_name=brand_name,
        status=LLMRankingAudit.STATUS_RUNNING,
        prompt_source=getattr(LLMRankingAudit, "PROMPT_SOURCE_LIBRARY", "library"),
        prompts=[prompt.text],
        providers_queried=[],
        started_at=timezone.now(),
    )

    queried_providers: list[str] = []
    try:
        variants = list_model_variants()
    except Exception:
        variants = []

    seen_providers: set[str] = set()
    for v in variants:
        if not getattr(v, "configured", False):
            continue
        provider_key = getattr(v, "provider", "")
        if not provider_key or provider_key in seen_providers:
            continue
        seen_providers.add(provider_key)
        cls = PROVIDERS.get(provider_key)
        if cls is None:
            continue
        try:
            instance = cls()
        except Exception as exc:
            errors.append(f"{provider_key}: {exc!s}")
            continue
        try:
            result = instance.query(prompt.text)
        except Exception as exc:
            errors.append(f"{provider_key}: {exc!s}")
            continue

        # A provider that returns succeeded=False (missing key, rate limit,
        # circuit open) still gets a row so the detail page can show the
        # state, but we skip extraction on it.
        succeeded = getattr(result, "succeeded", True)
        response_text = getattr(result, "text", None) or ""
        err = getattr(result, "error", "") or ""

        analysis = _extract_brands(
            response_text=response_text if succeeded else "",
            website=website,
            brand_name=brand_name,
            keywords=keywords,
            audit_id=str(audit.id),
        )

        result_obj = LLMRankingResult.objects.create(
            audit=audit,
            provider=provider_key,
            prompt_index=0,
            prompt=prompt.text,
            source_prompt=prompt,
            response_text=response_text,
            query_succeeded=succeeded,
            error_message=err[:500],
            is_mentioned=analysis["is_mentioned"],
            mention_rank=analysis["mention_rank"],
            sentiment=analysis["sentiment"],
            confidence_score=analysis["confidence_score"],
            mention_context=analysis["mention_context"],
            is_linked=analysis.get("is_linked", False),
            competitors_mentioned=analysis.get("competitors_mentioned", []),
            primary_recommendation=analysis.get("primary_recommendation", ""),
            citations=analysis.get("citations", []),
            extraction_model=analysis.get("extraction_model", ""),
            extraction_version=analysis.get("extraction_version", ""),
        )
        if succeeded:
            responses_logged += 1
            _dispatch_citations(result_obj.id)
        else:
            errors.append(f"{provider_key}: {err[:120]}")
        queried_providers.append(provider_key)

    audit.providers_queried = queried_providers
    audit.status = (
        LLMRankingAudit.STATUS_COMPLETED if responses_logged
        else LLMRankingAudit.STATUS_FAILED
    )
    audit.completed_at = timezone.now()
    audit.save(update_fields=["providers_queried", "status", "completed_at"])

    run.providers = queried_providers
    run.fanout_count = len(fanouts)
    run.source_count = responses_logged
    run.status = (
        PromptCrawlRun.STATUS_COMPLETE if responses_logged or fanouts
        else PromptCrawlRun.STATUS_FAILED
    )
    run.error = "; ".join(errors)[:1000]
    run.completed_at = timezone.now()
    run.save(update_fields=[
        "providers", "fanout_count", "source_count",
        "status", "error", "completed_at",
    ])

    return CrawlOutcome(fanouts=fanouts, responses=responses_logged, errors=errors)
