import logging
from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from apps.llm_ranking.api.v1.serializers import (
    CreateScheduleSerializer,
    LLMRankingAuditListSerializer,
    LLMRankingAuditSerializer,
    LLMRankingScheduleSerializer,
    RunAuditSerializer,
)
from apps.llm_ranking.models import LLMRankingAudit, LLMRankingSchedule
from core.views import TenantScopedAPIView, TenantScopedListAPIView

logger = logging.getLogger("apps")

FREQUENCY_DELTAS = {
    "weekly": timedelta(weeks=1),
    "biweekly": timedelta(weeks=2),
    "monthly": timedelta(days=30),
}


class LLMRankingAuditListView(TenantScopedListAPIView):
    """
    GET  — list all LLM ranking audits for a website (newest first).
    POST — create and queue a new audit.
    """

    def get(self, request, website_id):
        self.get_website(website_id)
        audits = LLMRankingAudit.objects.filter(website_id=website_id).order_by("-created_at")
        return self.paginated_response(audits, LLMRankingAuditListSerializer)

    def post(self, request, website_id):
        website = self.get_website(website_id)
        serializer = RunAuditSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        from apps.llm_ranking.services.ranking_service import LLMRankingService

        # Fall back to Website row fields when the client omits them. This is
        # the source of truth — the form doesn't need to resend what the
        # website already knows.
        business_name = data.get("business_name") or website.name
        industry = data.get("industry") or (website.industry or "")
        business_description = data.get("business_description") or (website.description or "")
        keywords = data.get("keywords") or (website.topics or [])

        if not business_name:
            return Response(
                {"error": "business_name is required (website has no name set)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not industry:
            return Response(
                {"error": "industry is required (set one on the website or pass it in the request)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Generate or use supplied prompts
        if data["custom_prompts"]:
            prompts = data["custom_prompts"]
        else:
            prompts = LLMRankingService.generate_prompts(
                business_name=business_name,
                industry=industry,
                description=business_description,
                keywords=keywords,
                use_case=data["use_case"],
                location=data.get("location", ""),
            )

        # Use selected providers or default to all
        selected_providers = data.get("providers") or ["claude", "gpt4", "gemini", "perplexity"]

        audit = LLMRankingAudit.objects.create(
            website=website,
            created_by=request.user,
            business_name=business_name,
            business_description=business_description,
            industry=industry,
            location=data.get("location", ""),
            keywords=keywords,
            prompts=prompts,
            providers_queried=selected_providers,
        )

        # Queue async task
        from apps.llm_ranking.tasks import run_llm_ranking_audit
        run_llm_ranking_audit.delay(audit_id=str(audit.id))

        return Response(
            LLMRankingAuditListSerializer(audit).data,
            status=status.HTTP_202_ACCEPTED,
        )


class LLMRankingPreviewPromptsView(TenantScopedAPIView):
    """
    GET — returns the prompts that `generate_prompts` would produce for this
    website without creating an audit. Used by the first-run UI to show users
    what will be asked before they commit to a paid run.
    """

    def get(self, request, website_id):
        from apps.llm_ranking.services.ranking_service import LLMRankingService

        website = self.get_website(website_id)
        industry = request.query_params.get("industry") or (website.industry or "")
        location = request.query_params.get("location") or ""
        use_case = request.query_params.get("use_case") or ""
        keywords = request.query_params.getlist("keywords") or (website.topics or [])

        prompts = LLMRankingService.generate_prompts(
            business_name=website.name,
            industry=industry,
            description=website.description or "",
            keywords=keywords,
            use_case=use_case,
            location=location,
        )
        return Response({
            "prompts": prompts,
            "source": {
                "business_name": website.name,
                "industry": industry,
                "description": website.description or "",
                "keywords": keywords,
                "location": location,
            },
        })


class LLMRankingAuditDetailView(TenantScopedAPIView):
    """
    GET    — retrieve audit with full per-LLM results.
    DELETE — delete audit record.
    """

    def _get_audit(self, website_id, audit_id):
        self.get_website(website_id)
        return self.get_tenant_object(
            LLMRankingAudit.objects.prefetch_related("results"),
            id=audit_id,
            website_id=website_id,
        )

    def get(self, request, website_id, audit_id):
        audit = self._get_audit(website_id, audit_id)
        return Response(LLMRankingAuditSerializer(audit).data)

    def delete(self, request, website_id, audit_id):
        audit = self._get_audit(website_id, audit_id)
        audit.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class LLMRankingRecommendationsView(TenantScopedAPIView):
    """GET — return actionable recommendations for improving LLM visibility."""

    def get(self, request, website_id, audit_id):
        self.get_website(website_id)
        audit = self.get_tenant_object(
            LLMRankingAudit.objects.prefetch_related("results"),
            id=audit_id,
            website_id=website_id,
        )

        if audit.status != LLMRankingAudit.STATUS_COMPLETED:
            return Response(
                {"error": "Audit has not completed yet."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.llm_ranking.services.ranking_service import LLMRankingService
        recs = LLMRankingService.generate_recommendations(audit=audit)
        return Response({"recommendations": recs, "overall_score": audit.overall_score})


class LLMRankingHistoryView(TenantScopedAPIView):
    """
    GET — return historical aggregate and per-provider stats for trend charts.
    """

    def get(self, request, website_id):
        self.get_website(website_id)
        audits = list(
            LLMRankingAudit.objects
            .filter(website_id=website_id, status=LLMRankingAudit.STATUS_COMPLETED)
            .order_by("completed_at")
            .values("id", "completed_at", "overall_score", "mention_rate",
                    "avg_mention_rank", "providers_queried")
        )
        if not audits:
            return Response([])

        audit_ids = [a["id"] for a in audits]
        stats_rows = (
            LLMRankingResult.objects
            .filter(audit_id__in=audit_ids, query_succeeded=True)
            .values("audit_id", "provider")
            .annotate(
                succeeded=Count("id"),
                mentioned=Count("id", filter=Q(is_mentioned=True)),
                avg_rank=Avg("mention_rank", filter=Q(is_mentioned=True)),
            )
        )

        by_audit: dict = {}
        for row in stats_rows:
            succeeded = row["succeeded"] or 0
            mentioned = row["mentioned"] or 0
            rate = round(mentioned / succeeded * 100, 1) if succeeded else 0.0
            by_audit.setdefault(row["audit_id"], []).append({
                "provider": row["provider"],
                "succeeded": succeeded,
                "mentioned": mentioned,
                "mention_rate": rate,
                "avg_rank": round(row["avg_rank"], 1) if row["avg_rank"] is not None else None,
            })

        for audit in audits:
            audit["providers"] = by_audit.get(audit["id"], [])

        return Response(audits)


class LLMRankingProviderBreakdownView(TenantScopedAPIView):
    """
    GET — per-provider mention stats for a completed audit.
    Useful for the tab's breakdown table.
    """

    def get(self, request, website_id, audit_id):
        self.get_website(website_id)
        audit = self.get_tenant_object(
            LLMRankingAudit.objects.prefetch_related("results"),
            id=audit_id,
            website_id=website_id,
        )

        from apps.llm_ranking.services.ranking_service import wilson_ci

        breakdown = {}
        for result in audit.results.all():
            p = result.provider
            if p not in breakdown:
                breakdown[p] = {
                    "provider": p,
                    "provider_display": result.get_provider_display(),
                    "total_prompts": 0,
                    "succeeded": 0,
                    "mentioned": 0,
                    "mention_rate": 0.0,
                    "mention_rate_ci_lower": 0.0,
                    "mention_rate_ci_upper": 0.0,
                    "avg_rank": None,
                    "sentiments": {"positive": 0, "neutral": 0, "negative": 0},
                }
            entry = breakdown[p]
            entry["total_prompts"] += 1
            if result.query_succeeded:
                entry["succeeded"] += 1
            if result.is_mentioned:
                entry["mentioned"] += 1
                if result.sentiment in entry["sentiments"]:
                    entry["sentiments"][result.sentiment] += 1

        # Compute derived fields: point estimate + 95% Wilson CI
        for entry in breakdown.values():
            if entry["succeeded"]:
                entry["mention_rate"] = round(
                    entry["mentioned"] / entry["succeeded"] * 100, 1
                )
                ci_low, ci_high = wilson_ci(entry["mentioned"], entry["succeeded"])
                entry["mention_rate_ci_lower"] = round(ci_low * 100, 1)
                entry["mention_rate_ci_upper"] = round(ci_high * 100, 1)
            ranks = [
                r.mention_rank
                for r in audit.results.filter(
                    provider=entry["provider"],
                    mention_rank__isnull=False,
                )
            ]
            if ranks:
                entry["avg_rank"] = round(sum(ranks) / len(ranks), 1)

        return Response(list(breakdown.values()))


class LLMRankingScheduleView(TenantScopedAPIView):
    """
    GET    — retrieve the current schedule for this website (or 404).
    POST   — create or update the schedule.
    DELETE — delete (disable) the schedule.
    """

    def get(self, request, website_id):
        self.get_website(website_id)
        try:
            schedule = LLMRankingSchedule.objects.get(website_id=website_id)
        except LLMRankingSchedule.DoesNotExist:
            return Response({"schedule": None})
        return Response({"schedule": LLMRankingScheduleSerializer(schedule).data})

    def post(self, request, website_id):
        website = self.get_website(website_id)
        serializer = CreateScheduleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        delta = FREQUENCY_DELTAS.get(data["frequency"], timedelta(weeks=1))
        now = timezone.now()

        schedule, created = LLMRankingSchedule.objects.update_or_create(
            website=website,
            defaults={
                "created_by": request.user,
                "is_enabled": data["is_enabled"],
                "frequency": data["frequency"],
                "business_name": data["business_name"],
                "business_description": data.get("business_description", ""),
                "industry": data["industry"],
                "location": data.get("location", ""),
                "keywords": data.get("keywords", []),
                "providers": data.get("providers", []),
                "next_run_at": now + delta,
            },
        )

        return Response(
            {"schedule": LLMRankingScheduleSerializer(schedule).data},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def delete(self, request, website_id):
        self.get_website(website_id)
        deleted, _ = LLMRankingSchedule.objects.filter(website_id=website_id).delete()
        if not deleted:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)
