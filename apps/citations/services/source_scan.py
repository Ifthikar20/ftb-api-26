"""
Source Intelligence scan orchestrator.

Runs the full pipeline for one SourceScan row:
  1. SERP: top web results for the query (Perplexity index).
  2. READ: per-URL content (Reddit JSON API or SSRF-guarded page fetch).
  3. UNDERSTAND: per-result brand/sentiment extraction (cheap LLM).
  4. AGGREGATE: cross-result share of voice on the scan row.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date

from django.utils import timezone

from apps.citations.models import SourceScan, SourceScanResult, SourceScanStatus
from apps.citations.services import content_reader, source_sentiment, web_search
from apps.citations.services.domain_classifier import _rule_classify
from apps.citations.services.url_normalizer import extract_apex_domain

logger = logging.getLogger("apps")

MAX_RESULTS_PER_SCAN = 10


def run_scan(scan: SourceScan) -> SourceScan:
    """Execute all stages. Always leaves the scan in COMPLETE or FAILED."""
    scan.status = SourceScanStatus.RUNNING
    scan.save(update_fields=["status", "updated_at"])

    website = scan.website
    target_brand = website.name or ""

    try:
        serp = web_search.search_web(
            scan.query,
            max_results=MAX_RESULTS_PER_SCAN,
            user_id=website.user_id,
        )
    except Exception as exc:  # defensive: search client normally returns []
        return _fail(scan, f"search failed: {exc}")

    if not serp:
        return _fail(
            scan,
            "no search results (Perplexity key missing, quota exhausted, or empty SERP)",
        )

    # SERP relevance gate: one batched judgement on titles/urls so
    # off-topic noise (designer "bags" on a "bagels" query) is dropped
    # before we pay for content fetches and per-result analysis.
    verdicts = source_sentiment.assess_serp_relevance(
        scan.query, serp, website=website, user=scan.created_by,
    )

    rows = []
    for item in serp:
        verdict = verdicts.get(item["rank"], {"relevant": True, "reason": ""})
        rows.append(SourceScanResult(
            scan=scan,
            rank=item["rank"],
            url=item["url"][:2000],
            domain=item["domain"][:300],
            source_class=_rule_classify(extract_apex_domain(item["domain"]), item["domain"]),
            serp_title=item["title"][:500],
            serp_snippet=item["snippet"],
            published_at=_parse_date(item.get("date")),
            last_updated_at=_parse_date(item.get("last_updated")),
            relevant=verdict["relevant"],
            relevance_note=verdict["reason"][:200],
        ))
    SourceScanResult.objects.bulk_create(rows)
    scan.results_count = len(rows)
    scan.save(update_fields=["results_count", "updated_at"])

    analyzed = 0
    for result in scan.results.all():
        if not result.relevant:
            result.analysis_error = "off_topic"
            result.save()
            continue

        content = content_reader.read_url(result.url)
        result.fetch_status = content["status"]
        result.content_kind = content["kind"]
        result.word_count = content["word_count"]
        if content["status"] != "ok" or not content["text"].strip():
            result.analysis_error = content["detail"] or "no content"
            result.save()
            continue

        analysis = source_sentiment.analyze_content(
            content["text"],
            query=scan.query,
            target_brand=target_brand,
            website=website,
            user=scan.created_by,
        )
        if analysis.get("error"):
            result.analysis_error = analysis["error"]
        elif not analysis.get("relevant_to_query", True):
            # Title looked on-topic but the content was not.
            result.relevant = False
            result.relevance_note = "content off-topic"
            result.analysis_error = "off_topic"
            result.brands = []
        else:
            result.brands = analysis["brands"]
            analyzed += 1
        result.save()

    scan.analyzed_count = analyzed
    scan.brands = _aggregate(scan, target_brand)
    scan.own_brand_present = any(
        b.get("is_own_brand") for b in scan.brands
    )
    scan.status = SourceScanStatus.COMPLETE
    scan.completed_at = timezone.now()
    scan.save()
    logger.info(
        "SourceScan %s complete: %d results, %d analyzed, %d brands",
        scan.pk, scan.results_count, analyzed, len(scan.brands),
    )
    return scan


def _fail(scan: SourceScan, message: str) -> SourceScan:
    scan.status = SourceScanStatus.FAILED
    scan.error = message[:1000]
    scan.completed_at = timezone.now()
    scan.save(update_fields=["status", "error", "completed_at", "updated_at"])
    logger.warning("SourceScan %s failed: %s", scan.pk, message)
    return scan


def _parse_date(value) -> date | None:
    """Parse a search-engine date string (ISO YYYY-MM-DD prefix) or None."""
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _matches_target(name: str, target: str) -> bool:
    """Fuzzy own-brand match: exact or substring either way, lowercased."""
    key = (name or "").strip().lower()
    target_lower = (target or "").strip().lower()
    if not key or not target_lower:
        return False
    return key == target_lower or target_lower in key or key in target_lower


def _aggregate(scan: SourceScan, target_brand: str) -> list[dict]:
    """Roll per-result brand extractions into a share-of-voice list.

    Rank-weighted: a mention in the #1 result counts more than one in
    the #10 result. Sentiment is a weight-averaged blend.
    """
    buckets: dict[str, dict] = defaultdict(
        lambda: {"mentions": 0, "weighted_score": 0.0, "sentiment_num": 0.0,
                 "sentiment_den": 0.0, "results_present_in": 0, "top_quote": "",
                 "top_quote_weight": -1.0, "issues": []}
    )
    for result in scan.results.filter(relevant=True):
        rank_weight = 1.0 / result.rank  # 1, .5, .33, ...
        for brand in result.brands or []:
            key = brand["name"].strip().lower()
            bucket = buckets[key]
            bucket.setdefault("name", brand["name"])
            contribution = rank_weight * (brand.get("weight") or 0.0)
            bucket["mentions"] += brand.get("mentions") or 0
            bucket["weighted_score"] += contribution
            bucket["sentiment_num"] += (brand.get("sentiment") or 0.0) * max(contribution, 0.01)
            bucket["sentiment_den"] += max(contribution, 0.01)
            bucket["results_present_in"] += 1
            quotes = brand.get("quotes") or []
            if quotes and contribution > bucket["top_quote_weight"]:
                bucket["top_quote"] = quotes[0]
                bucket["top_quote_weight"] = contribution
            for issue in brand.get("issues") or []:
                bucket["issues"].append((contribution, str(issue)))

    rollup = []
    for key, bucket in buckets.items():
        # Up to 5 issues, highest-contribution sources first, deduped
        # case-insensitively.
        seen: set[str] = set()
        issues = []
        for _, issue in sorted(bucket["issues"], key=lambda p: p[0], reverse=True):
            fold = issue.strip().lower()
            if fold and fold not in seen:
                seen.add(fold)
                issues.append(issue)
            if len(issues) >= 5:
                break
        rollup.append({
            "name": bucket["name"],
            "mentions": bucket["mentions"],
            "weighted_score": round(bucket["weighted_score"], 4),
            "sentiment": round(bucket["sentiment_num"] / bucket["sentiment_den"], 3)
            if bucket["sentiment_den"] else 0.0,
            "results_present_in": bucket["results_present_in"],
            "top_quote": bucket["top_quote"],
            "issues": issues,
            "is_own_brand": _matches_target(key, target_brand),
        })
    rollup.sort(key=lambda b: b["weighted_score"], reverse=True)
    return rollup[:25]


# Source classes where a brand can realistically join the conversation.
_ENGAGEABLE_CLASS_BOOST = {"reddit": 1.5, "forum": 1.5, "quora": 1.5}


def derive_opportunities(scan: SourceScan) -> list[dict]:
    """Sources where the conversation is active but the own brand is absent.

    Computed at read time (works retroactively on old scans, no schema).
    Score favors high-ranking sources with strong competitor presence,
    boosted for community sources the owner can actually post to.
    """
    target = scan.website.name or ""
    opportunities = []
    for result in scan.results.all():
        if not result.relevant or result.fetch_status != "ok":
            continue
        brands = result.brands or []
        if not brands or any(_matches_target(b.get("name", ""), target) for b in brands):
            continue

        weight_sum = sum(b.get("weight") or 0.0 for b in brands)
        boost = _ENGAGEABLE_CLASS_BOOST.get(result.source_class, 1.0)
        score = (1.0 / result.rank) * weight_sum * boost

        competitors = [b.get("name", "") for b in brands[:5]]
        issues = []
        for b in brands:
            issues.extend((b.get("issues") or [])[:2])
        kind = "community thread" if boost > 1.0 else "source"
        reason = (
            f"Active {kind} ranking #{result.rank} for this query mentions "
            f"{', '.join(competitors[:3])} but not {target or 'your brand'}."
        )
        opportunities.append({
            "rank": result.rank,
            "url": result.url,
            "domain": result.domain,
            "source_class": result.source_class,
            "serp_title": result.serp_title,
            "published_at": result.published_at.isoformat() if result.published_at else None,
            "competitors": competitors,
            "issues": issues[:5],
            "reason": reason,
            "score": round(score, 4),
        })
    opportunities.sort(key=lambda o: o["score"], reverse=True)
    return opportunities[:5]
