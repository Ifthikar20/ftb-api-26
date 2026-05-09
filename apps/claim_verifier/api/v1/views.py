"""REST endpoints for claim verification + the Accuracy dashboard."""
from __future__ import annotations

from collections import Counter
from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.claim_verifier.api.v1.serializers import (
    ClaimDetailSerializer,
    ClaimMismatchSerializer,
    ClaimSerializer,
)
from apps.claim_verifier.models import Claim, ClaimMismatch
from apps.llm_ranking.models import LLMRankingAudit
from core.exceptions import ResourceNotFound
from core.views import TenantScopedAPIView, TenantScopedListAPIView


def _get_audit_for_user(user, audit_id):
    from apps.websites.services.website_service import WebsiteService

    audit = get_object_or_404(LLMRankingAudit, id=audit_id)
    WebsiteService.get_for_user(user=user, website_id=audit.website_id)
    return audit


def _get_claim_for_user(user, claim_id):
    from apps.websites.services.website_service import WebsiteService

    try:
        claim = Claim.objects.select_related("website", "audit", "result").get(id=claim_id)
    except Claim.DoesNotExist as exc:
        raise ResourceNotFound("Claim not found.") from exc
    WebsiteService.get_for_user(user=user, website_id=claim.website_id)
    return claim


def _get_mismatch_for_user(user, mismatch_id):
    from apps.websites.services.website_service import WebsiteService

    try:
        mm = ClaimMismatch.objects.select_related("claim", "claim__website").get(id=mismatch_id)
    except ClaimMismatch.DoesNotExist as exc:
        raise ResourceNotFound("ClaimMismatch not found.") from exc
    WebsiteService.get_for_user(user=user, website_id=mm.claim.website_id)
    return mm


class WebsiteMismatchesView(TenantScopedListAPIView):
    """Paginated mismatches for a website."""

    def get(self, request, website_id):
        website = self.get_website(website_id)
        qs = ClaimMismatch.objects.filter(
            claim__website=website,
        ).select_related("claim", "claim__result", "matched_fact")

        severity = request.query_params.get("severity")
        if severity:
            qs = qs.filter(severity=severity)

        mtype = request.query_params.get("type") or request.query_params.get("mismatch_type")
        if mtype:
            qs = qs.filter(mismatch_type=mtype)

        product_line = request.query_params.get("product_line")
        if product_line:
            qs = qs.filter(matched_fact__product_line=product_line)

        since = request.query_params.get("since")
        if since:
            qs = qs.filter(created_at__date__gte=since)

        include_dismissed = (request.query_params.get("include_dismissed") or "").lower() in (
            "1", "true", "yes",
        )
        if not include_dismissed:
            qs = qs.filter(dismissed=False)

        qs = qs.order_by("-created_at")
        return self.paginated_response(qs, ClaimMismatchSerializer)


class WebsiteAccuracyView(TenantScopedAPIView):
    """Aggregate accuracy stats for the dashboard header + charts."""

    def get(self, request, website_id):
        website = self.get_website(website_id)
        period_days = int(request.query_params.get("period_days", 30) or 30)
        provider = request.query_params.get("provider")

        end = timezone.now().date()
        start = end - timedelta(days=period_days)

        claim_qs = Claim.objects.filter(
            website=website, created_at__date__gte=start,
        ).select_related("result")
        if provider:
            claim_qs = claim_qs.filter(result__provider=provider)

        total_claims = claim_qs.count()

        mm_qs = ClaimMismatch.objects.filter(
            claim__website=website, created_at__date__gte=start, dismissed=False,
        ).select_related("claim", "claim__result")
        if provider:
            mm_qs = mm_qs.filter(claim__result__provider=provider)

        mismatched = mm_qs.count()
        verified = max(0, total_claims - mismatched)
        accuracy_rate = round((verified / total_claims), 4) if total_claims else 1.0

        sev_counter: Counter = Counter()
        type_counter: Counter = Counter()
        provider_counter: Counter = Counter()
        for sev, mtype, prov in mm_qs.values_list(
            "severity", "mismatch_type", "claim__result__provider",
        ):
            sev_counter[sev] += 1
            type_counter[mtype] += 1
            if prov:
                provider_counter[prov] += 1

        # Trend — per-severity counts of mismatches per day.
        sev_keys = ("critical", "high", "medium", "low", "info")
        trend_buckets: dict[str, dict[str, int]] = {}
        # Seed every day in the period so the chart has continuous x-axis.
        cur = start
        while cur <= end:
            trend_buckets[cur.isoformat()] = {k: 0 for k in sev_keys}
            cur = cur + timedelta(days=1)
        for created, sev in mm_qs.values_list("created_at", "severity"):
            d = created.date().isoformat()
            row = trend_buckets.get(d)
            if row is None:
                row = {k: 0 for k in sev_keys}
                trend_buckets[d] = row
            if sev in row:
                row[sev] += 1
        trend_data = [
            {"date": d, "severity_breakdown": trend_buckets[d]}
            for d in sorted(trend_buckets.keys())
        ]

        return Response({
            "website_id": str(website.id),
            "period_days": period_days,
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "total_claims": total_claims,
            "verified": verified,
            "mismatched": mismatched,
            "accuracy_rate": accuracy_rate,
            "by_severity": dict(sev_counter),
            "by_type": dict(type_counter),
            "by_provider": dict(provider_counter),
            "trend": trend_data,
        })


class AuditClaimsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, audit_id):
        audit = _get_audit_for_user(request.user, audit_id)
        qs = (
            Claim.objects.filter(audit=audit)
            .select_related("result")
            .order_by("created_at")
        )
        return Response(ClaimSerializer(qs, many=True).data)


class ClaimDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, claim_id):
        claim = _get_claim_for_user(request.user, claim_id)
        return Response(ClaimDetailSerializer(claim).data)


_DISMISSAL_REASONS = {
    "false_positive", "not_about_us", "vault_outdated", "low_severity", "other",
}


class MismatchDismissView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, mismatch_id):
        mm = _get_mismatch_for_user(request.user, mismatch_id)
        reason = (request.data.get("reason") or "").strip()
        note = (request.data.get("note") or "").strip()
        if reason and reason not in _DISMISSAL_REASONS:
            from rest_framework import status as drf_status

            return Response(
                {"detail": f"Unknown dismissal reason '{reason}'."},
                status=drf_status.HTTP_400_BAD_REQUEST,
            )
        mm.dismissed = True
        mm.dismissed_at = timezone.now()
        mm.dismissal_reason = reason
        mm.dismissal_note = note
        mm.dismissed_by = request.user if getattr(request.user, "is_authenticated", False) else None
        mm.save(update_fields=[
            "dismissed", "dismissed_at",
            "dismissal_reason", "dismissal_note", "dismissed_by",
            "updated_at",
        ])
        return Response(ClaimMismatchSerializer(mm).data)


class WebsiteDismissalStatsView(TenantScopedAPIView):
    """Counts of dismissed mismatches by reason in the last N days."""

    def get(self, request, website_id):
        website = self.get_website(website_id)
        try:
            days = int(request.query_params.get("days", 30) or 30)
        except (TypeError, ValueError):
            days = 30
        since = timezone.now() - timedelta(days=days)
        qs = ClaimMismatch.objects.filter(
            claim__website=website, dismissed=True, dismissed_at__gte=since,
        )
        counter: Counter = Counter()
        for reason in qs.values_list("dismissal_reason", flat=True):
            counter[reason or "unspecified"] += 1
        return Response({
            "website_id": str(website.id),
            "days": days,
            "total_dismissed": sum(counter.values()),
            "by_reason": dict(counter),
        })
