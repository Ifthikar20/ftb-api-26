"""Brief generator — turns recommendation gaps into ContentBrief rows.

Two families of gaps are mined per website:

* Visibility — prompts where the target brand is mentioned in fewer than
  20% of recent provider results.
* Citation — source-class shares where the competitor share dwarfs the
  brand's share by more than 3x.

(The previous 'Accuracy' family — driven by claim_verifier mismatches —
was removed when the Accuracy product was retired.)

The generator is idempotent: each gap is hashed into a ``dedupe_key`` so
re-running for the same website does not create duplicate open / drafted
briefs for the same gap.
"""
from __future__ import annotations

import hashlib
import logging
from collections.abc import Iterable

from django.db import transaction

from apps.brand_vault.models import BrandFact, FactStatus
from apps.brand_vault.services.embeddings import cosine_similarity, embed_text
from apps.content_studio.models import (
    BriefStatus,
    ContentBrief,
    ContentFormat,
    GapType,
)

logger = logging.getLogger("apps")

VISIBILITY_THRESHOLD = 0.2
CITATION_RATIO_THRESHOLD = 3.0
ACTIVE_BRIEF_STATUSES = (BriefStatus.OPEN.value, BriefStatus.DRAFTED.value)


def _dedupe_key(gap_type: str, *parts: str) -> str:
    raw = "::".join([gap_type, *[(p or "") for p in parts]])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:64]


def _format_for_gap(gap_type: str, hint: str = "") -> str:
    if gap_type == GapType.CITATION.value:
        if hint and "reddit" in hint.lower():
            return ContentFormat.REDDIT_ANSWER.value
        return ContentFormat.BLOG.value
    return ContentFormat.BLOG.value


def _format_match_bonus(gap_type: str, fmt: str) -> float:
    if gap_type == GapType.CITATION.value and fmt in (
        ContentFormat.REDDIT_ANSWER.value, ContentFormat.BLOG.value,
    ):
        return 1.1
    return 1.0


def _severity_score(sev: str) -> float:
    return {
        "critical": 1.0,
        "high": 0.8,
        "medium": 0.5,
        "low": 0.3,
        "info": 0.1,
    }.get(sev or "", 0.4)


def _grounded_facts(website, query_text: str, *, limit: int = 8) -> list[BrandFact]:
    qs = BrandFact.objects.filter(
        website=website,
        status__in=(FactStatus.APPROVED.value, FactStatus.AUTO.value),
        version_to__isnull=True,
    )
    facts = list(qs[:200])
    if not facts:
        return []
    try:
        q_emb = embed_text(query_text)
    except Exception:
        q_emb = []
    if not q_emb:
        return facts[:limit]

    scored: list[tuple[float, BrandFact]] = []
    for f in facts:
        emb = f.embedding if isinstance(f.embedding, list) else None
        if not emb:
            scored.append((0.0, f))
            continue
        scored.append((cosine_similarity(q_emb, emb), f))
    scored.sort(key=lambda r: r[0], reverse=True)
    return [f for _, f in scored[:limit]]


def _existing_dedupe_keys(website) -> set[str]:
    return set(
        ContentBrief.objects.filter(
            website=website, status__in=ACTIVE_BRIEF_STATUSES,
        ).values_list("dedupe_key", flat=True),
    )


def _visibility_gaps(website) -> Iterable[dict]:
    """Yield prompt-level visibility gaps for the website's recent audits."""
    try:
        from apps.llm_ranking.models import LLMRankingAudit, LLMRankingResult
    except Exception:
        return
    audit = (
        LLMRankingAudit.objects.filter(website=website)
        .order_by("-created_at").first()
    )
    if not audit:
        return
    results = LLMRankingResult.objects.filter(audit=audit)
    by_prompt: dict[str, dict] = {}
    for r in results:
        key = (r.prompt or "")[:300]
        if not key:
            continue
        rec = by_prompt.setdefault(key, {"total": 0, "mentioned": 0, "prompt_obj": None})
        rec["total"] += 1
        if getattr(r, "is_mentioned", False) or getattr(r, "brand_mentioned", False):
            rec["mentioned"] += 1
        if rec["prompt_obj"] is None:
            rec["prompt_obj"] = getattr(r, "prompt_obj", None)

    for prompt_text, rec in by_prompt.items():
        if rec["total"] < 1:
            continue
        rate = rec["mentioned"] / rec["total"]
        if rate >= VISIBILITY_THRESHOLD:
            continue
        yield {
            "prompt_text": prompt_text,
            "prompt_obj": rec["prompt_obj"],
            "mention_rate": rate,
        }


def _citation_gaps(website) -> list[dict]:
    """Source-class gaps where a competitor outperforms the brand by 3x.

    The recommendation engine and citations app expose snapshots; if the
    expected models aren't reachable we just yield an empty list rather
    than failing brief generation.
    """
    try:
        from apps.citations.models import SourceInfluenceSnapshot  # type: ignore
    except Exception:
        return []
    try:
        snaps = (
            SourceInfluenceSnapshot.objects.filter(website=website)
            .order_by("-created_at")[:50]
        )
    except Exception:
        return []
    out: list[dict] = []
    for s in snaps:
        your_share = float(getattr(s, "your_share", 0.0) or 0.0)
        comp_share = float(getattr(s, "competitor_share", 0.0) or 0.0)
        source_class = getattr(s, "source_class", "") or ""
        if your_share <= 0 and comp_share <= 0:
            continue
        ratio = comp_share / your_share if your_share > 0 else CITATION_RATIO_THRESHOLD + 1
        if ratio < CITATION_RATIO_THRESHOLD:
            continue
        out.append({
            "source_class": source_class,
            "your_share": your_share,
            "competitor_share": comp_share,
        })
    return out


def _build_visibility_brief(website, gap, existing_keys) -> ContentBrief | None:
    prompt_obj = gap["prompt_obj"]
    prompt_text = gap["prompt_text"]
    fmt = _format_for_gap(GapType.VISIBILITY.value)
    dedupe_key = _dedupe_key(
        GapType.VISIBILITY.value,
        str(getattr(prompt_obj, "id", "")) or prompt_text[:80],
    )
    if dedupe_key in existing_keys:
        return None
    headline = f"Increase visibility for: {prompt_text[:200]}"
    description = (
        f"Brand is mentioned in only {gap['mention_rate'] * 100:.0f}% of "
        f"recent provider results for this prompt. Publish content that "
        f"addresses the underlying user intent and aligns with the brand's "
        f"approved facts."
    )
    structure = {"sections": [
        {"heading": "Direct answer to the question", "summary": "1-2 sentences"},
        {"heading": "Why this matters", "summary": "context and stakes"},
        {"heading": "How the brand approaches it", "summary": "grounded in vault facts"},
        {"heading": "Steps / examples", "summary": "concrete walkthrough"},
        {"heading": "Summary + call to action", "summary": "wrap-up"},
    ]}
    keywords = [w for w in prompt_text.lower().split() if len(w) > 3][:8]
    sev = 1.0 - gap["mention_rate"]
    impact = sev * 1.0 * _format_match_bonus(GapType.VISIBILITY.value, fmt)

    facts = _grounded_facts(website, prompt_text)
    brief = ContentBrief.objects.create(
        website=website,
        gap_type=GapType.VISIBILITY.value,
        impact_score=impact,
        target_format=fmt,
        target_prompt=prompt_obj if prompt_obj is not None else None,
        headline=headline[:300],
        description=description,
        suggested_structure=structure,
        target_keywords=keywords,
        dedupe_key=dedupe_key,
    )
    if facts:
        brief.grounded_facts.set(facts)
    existing_keys.add(dedupe_key)
    return brief


def _build_citation_brief(website, gap, existing_keys) -> ContentBrief | None:
    source_class = gap["source_class"] or "general"
    fmt = _format_for_gap(GapType.CITATION.value, hint=source_class)
    dedupe_key = _dedupe_key(GapType.CITATION.value, source_class)
    if dedupe_key in existing_keys:
        return None
    headline = f"Build citation share in {source_class}"
    description = (
        f"Competitors are cited {gap['competitor_share']:.2f} vs the brand's "
        f"{gap['your_share']:.2f} in {source_class}. Publish targeted content "
        f"to grow representation."
    )
    structure = {"sections": [
        {"heading": "Topic context", "summary": "what readers in this source need"},
        {"heading": "Brand perspective", "summary": "grounded answer"},
        {"heading": "Evidence", "summary": "citations and data"},
        {"heading": "Closing thought", "summary": "shareable takeaway"},
    ]}
    keywords = [source_class]
    your_share = max(gap["your_share"], 1e-6)
    impact = min(gap["competitor_share"] / your_share, 10.0) * 0.1 * _format_match_bonus(
        GapType.CITATION.value, fmt,
    )

    facts = _grounded_facts(website, source_class)
    brief = ContentBrief.objects.create(
        website=website,
        gap_type=GapType.CITATION.value,
        impact_score=impact,
        target_format=fmt,
        target_source_class=source_class,
        headline=headline[:300],
        description=description,
        suggested_structure=structure,
        target_keywords=keywords,
        dedupe_key=dedupe_key,
    )
    if facts:
        brief.grounded_facts.set(facts)
    existing_keys.add(dedupe_key)
    return brief


@transaction.atomic
def generate_briefs_for_website(website_id: str, limit: int = 20) -> int:
    """Pull top gaps and create ``ContentBrief`` rows. Returns count created."""
    from apps.websites.models import Website

    try:
        website = Website.objects.get(id=website_id)
    except Website.DoesNotExist:
        logger.info("generate_briefs_for_website: website %s not found", website_id)
        return 0

    existing_keys = _existing_dedupe_keys(website)
    created: list[ContentBrief] = []

    for gap in _visibility_gaps(website):
        if len(created) >= limit:
            break
        brief = _build_visibility_brief(website, gap, existing_keys)
        if brief is not None:
            created.append(brief)

    for gap in _citation_gaps(website):
        if len(created) >= limit:
            break
        brief = _build_citation_brief(website, gap, existing_keys)
        if brief is not None:
            created.append(brief)

    # Sort and trim is the caller's job; we just report count.
    return len(created)
