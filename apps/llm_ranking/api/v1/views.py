import logging

from django.conf import settings
from django.db.models import Avg, Count, Q
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.llm_ranking.api.v1.serializers import (
    LLMRankingAuditListSerializer,
    LLMRankingAuditSerializer,
    RunAuditSerializer,
)
from apps.llm_ranking.models import LLMRankingAudit, LLMRankingResult
from core.views import TenantScopedAPIView, TenantScopedListAPIView

logger = logging.getLogger("apps")


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

        # Generate or use supplied prompts
        if data["custom_prompts"]:
            prompts = data["custom_prompts"]
        else:
            prompts = LLMRankingService.generate_prompts(
                business_name=data["business_name"],
                industry=data["industry"],
                description=data["business_description"],
                keywords=data["keywords"],
                use_case=data["use_case"],
                location=data.get("location", ""),
                themes=data.get("themes") or None,
            )

        # Use selected providers or default to all
        selected_providers = data.get("providers") or ["claude", "gpt4", "gemini", "perplexity"]

        audit = LLMRankingAudit.objects.create(
            website=website,
            created_by=request.user,
            business_name=data["business_name"],
            business_description=data["business_description"],
            industry=data["industry"],
            location=data.get("location", ""),
            keywords=data["keywords"],
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
    GET — return historical aggregate, per-provider, and per-competitor stats
    for trend charts. The competitor visibility series powers the Brand
    Overview "Competitor Visibility" multi-line chart.
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

        # Per-provider stats per audit (existing)
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
        provider_by_audit: dict = {}
        for row in stats_rows:
            succeeded = row["succeeded"] or 0
            mentioned = row["mentioned"] or 0
            rate = round(mentioned / succeeded * 100, 1) if succeeded else 0.0
            provider_by_audit.setdefault(row["audit_id"], []).append({
                "provider": row["provider"],
                "succeeded": succeeded,
                "mentioned": mentioned,
                "mention_rate": rate,
                "avg_rank": round(row["avg_rank"], 1) if row["avg_rank"] is not None else None,
            })

        # Per-competitor visibility per audit. competitors_mentioned is a
        # JSONField list[dict], so we have to iterate in Python rather than
        # aggregate via the ORM.
        competitor_by_audit: dict = {}
        per_audit_total: dict = {}
        per_audit_self_brand_mentions: dict = {}
        per_audit_total_brand_mentions: dict = {}

        rows = (
            LLMRankingResult.objects
            .filter(audit_id__in=audit_ids, query_succeeded=True)
            .values("audit_id", "competitors_mentioned", "is_mentioned")
        )
        for r in rows:
            aid = r["audit_id"]
            per_audit_total[aid] = per_audit_total.get(aid, 0) + 1

            comps = r["competitors_mentioned"] or []
            # Total brand mentions across all responses for this audit =
            #   self mentions + competitor mentions. Used for citation share.
            self_mention = 1 if r["is_mentioned"] else 0
            per_audit_self_brand_mentions[aid] = (
                per_audit_self_brand_mentions.get(aid, 0) + self_mention
            )
            per_audit_total_brand_mentions[aid] = (
                per_audit_total_brand_mentions.get(aid, 0) + self_mention + len(comps)
            )

            seen_in_response: set = set()
            for c in comps:
                if not isinstance(c, dict):
                    continue
                name = (c.get("name") or "").strip()
                if not name or name in seen_in_response:
                    continue
                seen_in_response.add(name)
                key = (aid, name)
                if key not in competitor_by_audit:
                    competitor_by_audit[key] = {"count": 0, "ranks": []}
                competitor_by_audit[key]["count"] += 1
                pos = c.get("position")
                if isinstance(pos, (int, float)) and pos is not None:
                    competitor_by_audit[key]["ranks"].append(int(pos))

        # Group into per-audit lists.
        comp_list_by_audit: dict = {}
        for (aid, name), v in competitor_by_audit.items():
            total_prompts = max(per_audit_total.get(aid, 0), 1)
            visibility = round(v["count"] / total_prompts * 100, 1)
            avg_rank = (
                round(sum(v["ranks"]) / len(v["ranks"]), 1)
                if v["ranks"] else None
            )
            comp_list_by_audit.setdefault(aid, []).append({
                "name": name,
                "mention_count": v["count"],
                "visibility": visibility,
                "avg_rank": avg_rank,
            })

        # Citation share: self-brand mentions / total brand mentions across
        # all responses (us + competitors). Surfaces "of all brand citations
        # in AI answers, what share are us?"
        for aid in audit_ids:
            total = per_audit_total_brand_mentions.get(aid, 0)
            our = per_audit_self_brand_mentions.get(aid, 0)
            share = round(our / total * 100, 1) if total else 0.0
            for audit in audits:
                if audit["id"] == aid:
                    audit["citation_share"] = share
                    audit["citation_total"] = total
                    audit["citation_self"] = our
                    break

        for audit in audits:
            audit["providers"] = provider_by_audit.get(audit["id"], [])
            comps_for_audit = comp_list_by_audit.get(audit["id"], [])
            comps_for_audit.sort(key=lambda c: c["mention_count"], reverse=True)
            audit["competitors"] = comps_for_audit
            audit.setdefault("citation_share", 0.0)
            audit.setdefault("citation_total", 0)
            audit.setdefault("citation_self", 0)

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


class LLMRankingProviderHealthView(APIView):
    """
    GET — return the configuration status of each LLM provider so the UI
    can warn the user up-front when an API key is missing, instead of
    silently failing every query for that provider mid-audit.

    We do NOT make a live API call here (that would cost money on every
    page load); we just check whether the relevant settings exist. A
    deeper "ping" probe could be added later behind a query flag.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        providers = [
            {
                "key": "claude",
                "name": "Claude (Anthropic)",
                "model": "claude-sonnet-4-20250514",
                "configured": bool(getattr(settings, "ANTHROPIC_API_KEY", "")),
                "settings_key": "ANTHROPIC_API_KEY",
            },
            {
                "key": "gpt4",
                "name": "GPT-4 (OpenAI)",
                "model": "gpt-4o-mini",
                "configured": bool(getattr(settings, "OPENAI_API_KEY", "")),
                "settings_key": "OPENAI_API_KEY",
            },
            {
                "key": "gemini",
                "name": "Gemini (Google)",
                "model": "gemini-1.5-flash",
                "configured": bool(getattr(settings, "GEMINI_API_KEY", "")),
                "settings_key": "GEMINI_API_KEY",
            },
            {
                "key": "perplexity",
                "name": "Perplexity",
                "model": "llama-3.1-sonar-small-128k-online",
                "configured": bool(getattr(settings, "PERPLEXITY_API_KEY", "")),
                "settings_key": "PERPLEXITY_API_KEY",
            },
        ]
        configured_count = sum(1 for p in providers if p["configured"])
        return Response({
            "providers": providers,
            "configured_count": configured_count,
            "total": len(providers),
        })
