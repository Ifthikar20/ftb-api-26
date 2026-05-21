"""REST endpoints for citations and source-influence rollups.

All website-scoped endpoints inherit :class:`TenantScopedAPIView` so the
caller must own (or have access to) the website. Audit-scoped endpoints
go through the same gate by resolving the audit's website first.
"""
from __future__ import annotations

from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.citations.api.v1.serializers import (
    CitationSerializer,
    SourceInfluenceSnapshotSerializer,
)
from apps.citations.models import (
    Citation,
    SourceClass,
    SourceInfluenceSnapshot,
)
from apps.citations.services.snapshot_service import compute_audit_breakdown
from apps.llm_ranking.models import LLMRankingAudit
from core.views import TenantScopedAPIView, TenantScopedListAPIView


def _get_audit_for_user(user, audit_id):
    """Return the audit if its website belongs to ``user``, else 404."""
    from apps.websites.services.website_service import WebsiteService

    audit = get_object_or_404(LLMRankingAudit, id=audit_id)
    # Will raise 404/403 if the user does not own the website.
    WebsiteService.get_for_user(user=user, website_id=audit.website_id)
    return audit


class AuditCitationsView(TenantScopedListAPIView):
    """List citations for one audit. Filterable by provider + source_class."""

    def get(self, request, audit_id):
        audit = _get_audit_for_user(request.user, audit_id)
        qs = Citation.objects.filter(audit=audit).select_related("result")

        provider = request.query_params.get("provider")
        if provider:
            qs = qs.filter(result__provider=provider)

        source_class = request.query_params.get("source_class")
        if source_class:
            qs = qs.filter(source_class=source_class)

        qs = qs.order_by("position", "id")
        return self.paginated_response(qs, CitationSerializer)


class AuditSourceInfluenceView(APIView):
    """Live (non-persisted) breakdown for one audit."""

    permission_classes = [IsAuthenticated]

    def get(self, request, audit_id):
        audit = _get_audit_for_user(request.user, audit_id)
        return Response(compute_audit_breakdown(audit))


class WebsiteSourceInfluenceView(TenantScopedAPIView):
    """Per-website rollup over the trailing window.

    Returns a fully aggregated payload (totals, breakdown, top_domains,
    your_site_share, competitor_share, by_provider). Raw snapshots are
    only included when ``?include_raw=true`` is passed; the field is
    always present (possibly empty list) for backwards compatibility.
    """

    def get(self, request, website_id):
        from collections import Counter

        website = self.get_website(website_id)
        period_days = int(request.query_params.get("period_days", 30) or 30)
        provider = request.query_params.get("provider")
        include_raw = request.query_params.get("include_raw", "").lower() in (
            "1", "true", "yes",
        )

        end = timezone.now().date()
        start = end - timedelta(days=period_days)

        # Live citation rollup (always fresh).
        cit_qs = Citation.objects.filter(
            audit__website=website,
            created_at__date__gte=start,
            created_at__date__lte=end,
        ).select_related("result").only(
            "source_class", "apex_domain", "is_target", "is_competitor",
            "result__provider",
        )
        if provider:
            cit_qs = cit_qs.filter(result__provider=provider)

        cls_counter: Counter = Counter()
        domain_counter: Counter = Counter()
        domain_class_counter: dict[str, Counter] = {}
        domain_target: dict[str, int] = {}
        domain_competitor: dict[str, int] = {}
        per_provider: dict[str, dict] = {}
        your_site_count = 0
        competitor_count = 0
        total = 0

        for row in cit_qs:
            total += 1
            cls_counter[row.source_class] += 1
            if row.is_target:
                your_site_count += 1
            if row.is_competitor:
                competitor_count += 1
            d = row.apex_domain
            if d:
                domain_counter[d] += 1
                domain_class_counter.setdefault(d, Counter())[row.source_class] += 1
                if row.is_target:
                    domain_target[d] = domain_target.get(d, 0) + 1
                if row.is_competitor:
                    domain_competitor[d] = domain_competitor.get(d, 0) + 1
            prov = row.result.provider
            pp = per_provider.setdefault(prov, {
                "total_citations": 0,
                "_cls": Counter(),
                "_domains": Counter(),
                "_domain_cls": {},
                "_domain_target": {},
                "_domain_competitor": {},
            })
            pp["total_citations"] += 1
            pp["_cls"][row.source_class] += 1
            if d:
                pp["_domains"][d] += 1
                pp["_domain_cls"].setdefault(d, Counter())[row.source_class] += 1
                if row.is_target:
                    pp["_domain_target"][d] = pp["_domain_target"].get(d, 0) + 1
                if row.is_competitor:
                    pp["_domain_competitor"][d] = pp["_domain_competitor"].get(d, 0) + 1

        breakdown: dict = {}
        if total:
            for cls, count in cls_counter.items():
                breakdown[cls] = {
                    "count": count,
                    "share": round(count / total, 4),
                }

        top_domains = []
        for d, c in domain_counter.most_common(50):
            cls_for_domain = "other"
            if d in domain_class_counter and domain_class_counter[d]:
                cls_for_domain = domain_class_counter[d].most_common(1)[0][0]
            top_domains.append({
                "apex_domain": d,
                "count": c,
                "share": round(c / total, 4) if total else 0,
                "source_class": cls_for_domain,
                "is_target": domain_target.get(d, 0) > 0,
                "is_competitor": domain_competitor.get(d, 0) > 0,
            })

        by_provider: dict[str, dict] = {}
        for prov, pp in per_provider.items():
            ptotal = pp["total_citations"]
            pbreakdown: dict = {}
            for cls, count in pp["_cls"].items():
                pbreakdown[cls] = {
                    "count": count,
                    "share": round(count / ptotal, 4) if ptotal else 0,
                }
            ptop = []
            for d, c in pp["_domains"].most_common(50):
                cls_for_d = "other"
                if d in pp["_domain_cls"] and pp["_domain_cls"][d]:
                    cls_for_d = pp["_domain_cls"][d].most_common(1)[0][0]
                ptop.append({
                    "apex_domain": d,
                    "count": c,
                    "share": round(c / ptotal, 4) if ptotal else 0,
                    "source_class": cls_for_d,
                    "is_target": pp["_domain_target"].get(d, 0) > 0,
                    "is_competitor": pp["_domain_competitor"].get(d, 0) > 0,
                })
            by_provider[prov] = {
                "total_citations": ptotal,
                "breakdown": pbreakdown,
                "top_domains": ptop,
            }

        # Snapshots (kept for backwards compat).
        snap_qs = SourceInfluenceSnapshot.objects.filter(
            website=website,
            period_end__gte=start,
        ).order_by("-period_end")
        if provider:
            snap_qs = snap_qs.filter(provider=provider)
        snapshots_data = (
            SourceInfluenceSnapshotSerializer(snap_qs, many=True).data
            if include_raw
            else []
        )

        return Response({
            "website_id": str(website.id),
            "period_days": period_days,
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "total_citations": total,
            "unique_domains": len(domain_counter),
            "your_site_share": round(your_site_count / total, 4) if total else 0,
            "competitor_share": round(competitor_count / total, 4) if total else 0,
            "breakdown": breakdown,
            "top_domains": top_domains,
            "by_provider": by_provider,
            "snapshots": snapshots_data,
        })


class WebsiteCitationsView(TenantScopedListAPIView):
    """Paginated raw citations across every audit on a website."""

    def get(self, request, website_id):
        website = self.get_website(website_id)
        qs = Citation.objects.filter(audit__website=website).select_related("result")

        provider = request.query_params.get("provider")
        if provider:
            qs = qs.filter(result__provider=provider)

        source_class = request.query_params.get("source_class")
        if source_class:
            qs = qs.filter(source_class=source_class)

        since = request.query_params.get("since")
        if since:
            qs = qs.filter(created_at__date__gte=since)

        qs = qs.order_by("-created_at")
        return self.paginated_response(qs, CitationSerializer)


class GlobalSourceInfluenceView(APIView):
    """Global (cross-tenant) rollup for benchmarking. No PII; safe to expose."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        provider = request.query_params.get("provider")
        industry_id = request.query_params.get("industry")
        period_days = int(request.query_params.get("period_days", 30) or 30)

        end = timezone.now().date()
        start = end - timedelta(days=period_days)

        qs = SourceInfluenceSnapshot.objects.filter(
            website__isnull=True,
            period_end__gte=start,
        ).order_by("-period_end")
        if provider:
            qs = qs.filter(provider=provider)
        if industry_id:
            qs = qs.filter(industry_id=industry_id)

        return Response({
            "period_days": period_days,
            "snapshots": SourceInfluenceSnapshotSerializer(qs, many=True).data,
            "source_classes": [
                {"value": v, "label": label} for v, label in SourceClass.choices
            ],
        })
