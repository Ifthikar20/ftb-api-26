"""Match Claims against the BrandVault and produce ClaimMismatches.

The MVP verifier is intentionally simple — embedding cosine similarity
to retrieve top candidate facts, then a string-overlap check on the
object to decide whether the claim agrees, contradicts, or is unknown.
Severity is derived from a product of factual divergence and an audience
reach term that is currently a placeholder (1.0) — refinement is a
follow-up phase once we have provider-weighting + prompt-frequency.
"""
from __future__ import annotations

import logging
from typing import Optional

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
            # Lexical fallback when embedding dims differ or are missing.
            sim = _overlap(
                f"{claim.subject} {claim.predicate}",
                f"{fact.subject} {fact.predicate}",
            )
        if sim > best_sim:
            best, best_sim = fact, sim
    return best, best_sim


def verify_claim(claim_id: str) -> Optional[ClaimMismatch]:
    """Return the persisted ClaimMismatch, or None if claim agrees."""
    try:
        claim = Claim.objects.select_related("website", "audit", "result").get(id=claim_id)
    except Claim.DoesNotExist:
        return None

    fact, sim = _best_match(claim)

    if fact is None or sim < _SIMILAR_THRESHOLD:
        # Nothing close in the vault.
        divergence = 0.5
        score = divergence * 1.0
        severity = bucket(score)
        explanation = "No matching fact found in the brand vault."
        return _upsert_mismatch(
            claim,
            matched_fact=None,
            mismatch_type=MismatchType.UNKNOWN.value,
            severity=severity,
            divergence=divergence,
            explanation=explanation,
        )

    # subject+predicate align reasonably; check the object.
    object_overlap = _overlap(claim.object, fact.object)
    if object_overlap >= _OBJECT_OVERLAP_THRESHOLD:
        # Agrees — clean up any stale mismatch row, return None.
        ClaimMismatch.objects.filter(claim=claim).delete()
        return None

    divergence = 1.0 - object_overlap
    score = divergence * 1.0
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
        explanation=explanation,
    )


def _upsert_mismatch(
    claim: Claim,
    *,
    matched_fact,
    mismatch_type: str,
    severity: str,
    divergence: float,
    explanation: str,
) -> ClaimMismatch:
    mm, _ = ClaimMismatch.objects.update_or_create(
        claim=claim,
        defaults={
            "matched_fact": matched_fact,
            "mismatch_type": mismatch_type,
            "severity": severity,
            "factual_divergence": divergence,
            "audience_reach": 1.0,
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
