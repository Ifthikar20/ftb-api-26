"""Match Claims against the BrandVault and produce ClaimMismatches.

The MVP verifier is intentionally simple — embedding cosine similarity
to retrieve top candidate facts, then a string-overlap check on the
object to decide whether the claim agrees, contradicts, or is unknown.

Severity is the product of factual divergence and an audience-reach
weight; see :func:`compute_audience_reach` below.
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Optional

from django.utils import timezone

from apps.brand_vault.models import BrandFact, FactStatus
from apps.brand_vault.services.embeddings import cosine_similarity, embed_text
from apps.claim_verifier.models import (
    Claim,
    ClaimMismatch,
    MismatchSeverity,
    MismatchType,
)
from apps.claim_verifier.services.severity import bucket

logger = logging.getLogger("apps")


_SIMILAR_THRESHOLD = 0.55
_OBJECT_OVERLAP_THRESHOLD = 0.4

# Provider weights — calibrated against rough internal traffic estimates.
# Claude and GPT each get the largest slice; Gemini sits just below;
# Perplexity is the smallest share but still meaningful for citations.
# Update these as the traffic mix changes.
PROVIDER_WEIGHTS: dict[str, float] = {
    "claude": 0.30,
    "anthropic": 0.30,
    "gpt": 0.30,
    "openai": 0.30,
    "gemini": 0.25,
    "google": 0.25,
    "perplexity": 0.15,
}

# Above this many same-prompt rows in the period, prompt_frequency saturates.
_PROMPT_FREQ_SATURATION = 20

# Lookback window for prompt-frequency normalization.
_PROMPT_FREQ_DAYS = 30


def _tokens(text: str) -> set[str]:
    return {t for t in (text or "").lower().split() if len(t) > 2}


def _overlap(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / max(1, len(ta | tb))


def _claim_embedding(claim: Claim) -> list[float]:
    if claim.embedding:
        return list(claim.embedding)
    return embed_text(f"{claim.subject} {claim.predicate} {claim.object}")


def _candidate_facts(claim: Claim) -> list[BrandFact]:
    return list(
        BrandFact.objects.filter(
            website=claim.website,
            status__in=[FactStatus.APPROVED, FactStatus.AUTO],
            version_to__isnull=True,
        )
    )


def _best_match(claim: Claim) -> tuple[Optional[BrandFact], float]:
    cvec = _claim_embedding(claim)
    best, best_sim = None, 0.0
    for fact in _candidate_facts(claim):
        fvec = fact.embedding or []
        if cvec and fvec and len(cvec) == len(fvec):
            sim = cosine_similarity(cvec, fvec)
        else:
            sim = _overlap(
                f"{claim.subject} {claim.predicate}",
                f"{fact.subject} {fact.predicate}",
            )
        if sim > best_sim:
            best, best_sim = fact, sim
    return best, best_sim


def _provider_weight(provider: str) -> float:
    if not provider:
        return 0.20
    key = provider.strip().lower()
    if key in PROVIDER_WEIGHTS:
        return PROVIDER_WEIGHTS[key]
    # try fuzzy startswith match (e.g. "gpt-4" -> "gpt")
    for k, v in PROVIDER_WEIGHTS.items():
        if key.startswith(k) or k in key:
            return v
    return 0.20


def _prompt_frequency(claim: Claim) -> int:
    """Count of LLMRankingResult rows with the same prompt text in last N days."""
    from apps.llm_ranking.models import LLMRankingResult

    prompt_text = getattr(claim.result, "prompt", "") or ""
    if not prompt_text:
        return 0
    since = timezone.now() - timedelta(days=_PROMPT_FREQ_DAYS)
    return LLMRankingResult.objects.filter(
        prompt=prompt_text, created_at__gte=since,
    ).count()


def _is_target_brand(claim: Claim) -> bool:
    """Return True if the claim subject mentions the website's brand."""
    subject = (claim.subject or "").lower()
    if not subject:
        return False
    audit = getattr(claim, "audit", None)
    candidates: list[str] = []
    if audit is not None:
        bn = getattr(audit, "business_name", "") or ""
        if bn:
            candidates.append(bn.lower())
    website = getattr(claim, "website", None)
    if website is not None:
        for attr in ("name", "domain", "brand_name"):
            val = getattr(website, attr, "") or ""
            if val:
                candidates.append(str(val).lower())
    for cand in candidates:
        cand_core = cand.replace("www.", "").split(".")[0].strip()
        if cand_core and cand_core in subject:
            return True
    return False


def compute_audience_reach(claim: Claim) -> float:
    """0.0 to 1.0. Higher = more visible/important.

    Components:
      - provider_weight: Claude/GPT = 0.30 each, Gemini = 0.25, Perplexity = 0.15
        (calibrate to your traffic estimates; stored in PROVIDER_WEIGHTS).
      - prompt_frequency: how often this prompt was sampled in last 30d
        (count of LLMRankingResult rows for the same prompt text in the period),
        normalized against a saturation point.
      - is_target_brand: 1.5x multiplier if claim.subject mentions the
        website's brand.

    Final: clamp(provider_weight * 0.5 + freq_normalized * 0.4 + brand_bonus * 0.1, 0, 1)
    Then multiplied by 1.5 (and clamped to 1.0) when the claim references the
    target brand directly.
    """
    provider = getattr(getattr(claim, "result", None), "provider", "") or ""
    pw = _provider_weight(provider)

    freq = _prompt_frequency(claim)
    freq_normalized = min(1.0, freq / float(_PROMPT_FREQ_SATURATION))

    brand_bonus = 1.0 if _is_target_brand(claim) else 0.0

    base = pw * 0.5 + freq_normalized * 0.4 + brand_bonus * 0.1
    if brand_bonus:
        base *= 1.5
    return max(0.0, min(1.0, base))


def verify_claim(claim_id: str) -> Optional[ClaimMismatch]:
    """Return the persisted ClaimMismatch, or None if claim agrees."""
    try:
        claim = Claim.objects.select_related("website", "audit", "result").get(id=claim_id)
    except Claim.DoesNotExist:
        return None

    fact, sim = _best_match(claim)

    audience_reach = compute_audience_reach(claim)

    if fact is None or sim < _SIMILAR_THRESHOLD:
        divergence = 0.5
        score = divergence * audience_reach
        severity = bucket(score)
        explanation = "No matching fact found in the brand vault."
        return _upsert_mismatch(
            claim,
            matched_fact=None,
            mismatch_type=MismatchType.UNKNOWN.value,
            severity=severity,
            divergence=divergence,
            audience_reach=audience_reach,
            explanation=explanation,
        )

    object_overlap = _overlap(claim.object, fact.object)
    if object_overlap >= _OBJECT_OVERLAP_THRESHOLD:
        ClaimMismatch.objects.filter(claim=claim).delete()
        return None

    divergence = 1.0 - object_overlap
    score = divergence * audience_reach
    severity = bucket(score)
    explanation = (
        f"Claim object '{claim.object[:120]}' diverges from vault fact "
        f"'{fact.object[:120]}' (overlap={object_overlap:.2f})."
    )
    return _upsert_mismatch(
        claim,
        matched_fact=fact,
        mismatch_type=MismatchType.CONTRADICTS.value,
        severity=severity,
        divergence=divergence,
        audience_reach=audience_reach,
        explanation=explanation,
    )


def _upsert_mismatch(
    claim: Claim,
    *,
    matched_fact,
    mismatch_type: str,
    severity: str,
    divergence: float,
    audience_reach: float,
    explanation: str,
) -> ClaimMismatch:
    mm, _ = ClaimMismatch.objects.update_or_create(
        claim=claim,
        defaults={
            "matched_fact": matched_fact,
            "mismatch_type": mismatch_type,
            "severity": severity,
            "factual_divergence": divergence,
            "audience_reach": audience_reach,
            "explanation": explanation,
            "dismissed": False,
        },
    )
    return mm


def verify_claims_for_audit(audit_id: str) -> int:
    """Iterate all claims for an audit, calling verify_claim on each."""
    qs = Claim.objects.filter(audit_id=audit_id).only("id")
    created = 0
    for claim_id in qs.values_list("id", flat=True):
        try:
            if verify_claim(str(claim_id)) is not None:
                created += 1
        except Exception as exc:  # pragma: no cover
            logger.warning("verify_claim(%s) failed: %s", claim_id, exc)
    return created
