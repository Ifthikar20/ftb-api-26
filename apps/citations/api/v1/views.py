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
    """Per-website rollup over the trailing window. Reads from snapshots."""

    def get(self, request, website_id):
        website = self.get_website(website_id)
        period_days = int(request.query_params.get("period_days", 30) or 30)
        provider = request.query_params.get("provider")

        end = timezone.now().date()
        start = end - timedelta(days=period_days)

        qs = SourceInfluenceSnapshot.objects.filter(
            website=website,
            period_end__gte=start,
        ).order_by("-period_end")
        if provider:
            qs = qs.filter(provider=provider)

        return Response({
            "website_id": str(website.id),
            "period_days": period_days,
            "snapshots": SourceInfluenceSnapshotSerializer(qs, many=True).data,
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
                {"value": v, "label": l} for v, l in SourceClass.choices
            ],
        })
