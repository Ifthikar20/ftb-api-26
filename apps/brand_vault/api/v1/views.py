"""REST endpoints for the Brand Vault."""
from __future__ import annotations

from collections import Counter

from django.db.models import Q
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.brand_vault.api.v1.serializers import (
    BrandFactDetailSerializer,
    BrandFactEditSerializer,
    BrandFactSerializer,
)
from apps.brand_vault.models import BrandFact, FactStatus
from apps.brand_vault.services import fact_versioning
from core.exceptions import ResourceNotFound
from core.views import TenantScopedAPIView, TenantScopedListAPIView


class WebsiteFactsView(TenantScopedListAPIView):
    """List facts for a website with status / product_line / topic filters."""

    def get(self, request, website_id):
        website = self.get_website(website_id)
        qs = BrandFact.objects.filter(website=website)

        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        product_line = request.query_params.get("product_line")
        if product_line:
            qs = qs.filter(product_line=product_line)

        topic = request.query_params.get("topic")
        if topic:
            qs = qs.filter(topic=topic)

        q = request.query_params.get("q")
        if q:
            qs = qs.filter(
                Q(subject__icontains=q) | Q(predicate__icontains=q)
                | Q(object__icontains=q),
            )

        only_current = request.query_params.get("only_current")
        if only_current and only_current.lower() in ("1", "true", "yes"):
            qs = qs.filter(version_to__isnull=True)

        qs = qs.order_by("-created_at")
        return self.paginated_response(qs, BrandFactSerializer)


def _get_fact_for_user(user, fact_id) -> BrandFact:
    from apps.websites.services.website_service import WebsiteService

    try:
        fact = BrandFact.objects.select_related("website").get(id=fact_id)
    except BrandFact.DoesNotExist as exc:
        raise ResourceNotFound("BrandFact not found.") from exc
    WebsiteService.get_for_user(user=user, website_id=fact.website_id)
    return fact


class FactDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, fact_id):
        fact = _get_fact_for_user(request.user, fact_id)
        return Response(BrandFactDetailSerializer(fact).data)


class FactApproveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, fact_id):
        fact = _get_fact_for_user(request.user, fact_id)
        fact = fact_versioning.approve_fact(str(fact.id), actor_user=request.user)
        return Response(BrandFactSerializer(fact).data)


class FactRejectView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, fact_id):
        fact = _get_fact_for_user(request.user, fact_id)
        fact = fact_versioning.reject_fact(str(fact.id), actor_user=request.user)
        return Response(BrandFactSerializer(fact).data)


class FactEditView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, fact_id):
        fact = _get_fact_for_user(request.user, fact_id)
        ser = BrandFactEditSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        new_fact = fact_versioning.supersede_fact(
            str(fact.id),
            ser.validated_data["subject"],
            ser.validated_data["predicate"],
            ser.validated_data["object"],
            actor_user=request.user,
        )
        return Response(BrandFactSerializer(new_fact).data, status=status.HTTP_201_CREATED)


class WebsiteExtractView(TenantScopedAPIView):
    """Trigger an LLM extraction pass over the website's KnowledgeChunks."""

    def post(self, request, website_id):
        website = self.get_website(website_id)
        try:
            from apps.brand_vault.tasks import extract_facts_for_website
            extract_facts_for_website.delay(str(website.id))
            queued = True
        except Exception:
            queued = False
        return Response({"queued": queued, "website_id": str(website.id)})


class WebsiteStatsView(TenantScopedAPIView):
    """Aggregate counts for the dashboard header."""

    def get(self, request, website_id):
        website = self.get_website(website_id)
        qs = BrandFact.objects.filter(website=website)

        by_status: Counter = Counter()
        by_product: Counter = Counter()
        by_topic: Counter = Counter()
        for s, pl, tp in qs.values_list("status", "product_line", "topic"):
            by_status[s] += 1
            if pl:
                by_product[pl] += 1
            if tp:
                by_topic[tp] += 1

        recent = qs.order_by("-created_at")[:5]
        recent_data = BrandFactSerializer(recent, many=True).data

        return Response({
            "website_id": str(website.id),
            "total": sum(by_status.values()),
            "by_status": {
                FactStatus.PENDING.value: by_status.get(FactStatus.PENDING.value, 0),
                FactStatus.APPROVED.value: by_status.get(FactStatus.APPROVED.value, 0),
                FactStatus.REJECTED.value: by_status.get(FactStatus.REJECTED.value, 0),
                FactStatus.AUTO.value: by_status.get(FactStatus.AUTO.value, 0),
            },
            "by_product_line": dict(by_product.most_common(20)),
            "by_topic": dict(by_topic.most_common(20)),
            "recent": recent_data,
        })
