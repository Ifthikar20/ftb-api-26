"""REST endpoints for the prompt library.

The API has two audiences:

* The onboarding flow + LLM Ranking dashboard, which need read-only
  access to industries and a paginated browse of prompts.
* The Run Audit modal, which previews and persists a per-audit
  prompt sample (a :class:`PromptSampleRun`).
"""
from __future__ import annotations

import random

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.llm_ranking.models import LLMRankingAudit
from apps.prompt_library.api.v1.serializers import (
    IndustrySerializer,
    PreviewSampleRequestSerializer,
    PromptSampleRunSerializer,
    PromptSerializer,
    UseLibrarySampleRequestSerializer,
)
from apps.prompt_library.models import Industry, Prompt, PromptSampleRun
from apps.prompt_library.services.sampler_service import sample_prompts_for_audit
from apps.websites.services.website_service import WebsiteService
from core.interceptors.pagination import StandardPagination


class IndustryListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = IndustrySerializer
    pagination_class = None

    def get_queryset(self):
        return Industry.objects.filter(is_active=True).order_by("name")


class PromptListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PromptSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = Prompt.objects.filter(is_active=True).select_related("industry")
        industry_slug = self.request.query_params.get("industry")
        if industry_slug:
            qs = qs.filter(industry__slug=industry_slug)
        intent = self.request.query_params.get("intent_bucket")
        if intent:
            qs = qs.filter(intent_bucket=intent)
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(text__icontains=search)
        return qs.order_by("-demand_score", "-created_at")


class PreviewSampleView(APIView):
    """Return a non-persisted sample for the Run Audit preview drawer."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PreviewSampleRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        industry = get_object_or_404(Industry, id=data["industry_id"], is_active=True)
        n = data["n"]
        seed = random.randint(0, 2**31 - 1)
        rng = random.Random(seed)

        pool = list(
            Prompt.objects.filter(industry=industry, is_active=True).order_by(
                "-demand_score", "-created_at"
            )[: max(n * 4, 50)]
        )
        rng.shuffle(pool)
        chosen = pool[:n]
        return Response(
            {
                "industry": IndustrySerializer(industry).data,
                "seed": seed,
                "strategy": data["strategy"],
                "prompts": PromptSerializer(chosen, many=True).data,
            }
        )


def _resolve_audit(user, audit_id) -> LLMRankingAudit:
    """Fetch an audit and verify the user owns the underlying website."""
    audit = get_object_or_404(LLMRankingAudit, id=audit_id)
    WebsiteService.get_for_user(user=user, website_id=audit.website_id)
    return audit


class UseLibrarySampleView(APIView):
    """Persist a PromptSampleRun on a draft audit and flip prompt_source."""

    permission_classes = [IsAuthenticated]

    def post(self, request, audit_id):
        audit = _resolve_audit(request.user, audit_id)
        serializer = UseLibrarySampleRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        industry = get_object_or_404(Industry, id=data["industry_id"], is_active=True)
        if audit.status not in (LLMRankingAudit.STATUS_PENDING,):
            return Response(
                {"error": "audit_not_draft", "detail": "Sample can only be set on a pending audit."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sample_run = sample_prompts_for_audit(
            audit_run=audit,
            industry=industry,
            n=data["n"],
            strategy=data["strategy"],
            seed=data.get("seed"),
        )
        # Default to library when the user explicitly opts in.
        if audit.prompt_source == LLMRankingAudit.PROMPT_SOURCE_VAULT:
            audit.prompt_source = LLMRankingAudit.PROMPT_SOURCE_LIBRARY
            audit.save(update_fields=["prompt_source"])
        return Response(PromptSampleRunSerializer(sample_run).data)


class GetAuditSampleView(APIView):
    """Return the persisted sample with provenance for the audit detail page."""

    permission_classes = [IsAuthenticated]

    def get(self, request, audit_id):
        audit = _resolve_audit(request.user, audit_id)
        sample_run = getattr(audit, "prompt_sample_run", None)
        if sample_run is None:
            return Response({"sample_run": None})
        return Response({"sample_run": PromptSampleRunSerializer(sample_run).data})
