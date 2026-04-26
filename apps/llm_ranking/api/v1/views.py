import logging
from datetime import timedelta

from django.conf import settings
from django.db.models import Avg, Count, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.llm_ranking.api.v1.serializers import (
    CreateScheduleSerializer,
    LLMRankingAuditListSerializer,
    LLMRankingAuditSerializer,
    LLMRankingScheduleSerializer,
    RunAuditSerializer,
)
from apps.llm_ranking.models import LLMRankingAudit, LLMRankingResult, LLMRankingSchedule
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
        from apps.llm_ranking.providers import PROVIDERS

        # Enforce per-user monthly AI spend cap before queuing more work.
        # 0 = no cap; spend covers every module that writes to AITokenUsage.
        cap = float(getattr(request.user, "monthly_ai_cost_cap_usd", 0) or 0)
        if cap > 0:
            from core.ai_tracking import month_to_date_cost
            spent = month_to_date_cost(request.user)
            if spent >= cap:
                return Response(
                    {
                        "error": "monthly_ai_cost_cap_exceeded",
                        "detail": (
                            f"Month-to-date AI spend ${spent:.2f} has reached "
                            f"your cap of ${cap:.2f}. Raise the cap in Settings "
                            f"or wait until the next billing month."
                        ),
                        "cap_status": {"spent_usd": round(spent, 4), "cap_usd": cap},
                    },
                    status=402,
                )

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
            # Tag custom prompts with "custom" type
            prompts = [{"text": p, "type": "custom"} for p in data["custom_prompts"]]
        else:
            prompts = LLMRankingService.generate_prompts(
                business_name=business_name,
                industry=industry,
                description=business_description,
                keywords=keywords,
                use_case=data["use_case"],
                location=data.get("location", ""),
                themes=data.get("themes") or None,
                user=request.user,
                website=website,
            )

        # Selected providers must be implemented AND configured. Stub providers
        # in PROVIDER_CHOICES (meta_llama, mistral, etc.) are filtered out so
        # the UI can never queue a run that would silently produce no results.
        requested = data.get("providers") or list(PROVIDERS.keys())
        configured = []
        for key in requested:
            if key not in PROVIDERS:
                continue
            cls = PROVIDERS[key]
            if getattr(settings, cls.api_key_setting, ""):
                configured.append(key)
        selected_providers = configured or ["claude"]

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
            context_urls=data.get("context_urls", []),
        )

        # Dispatch: in production use Celery, in dev the user triggers
        # the run manually via the "Run" button (retry endpoint) because
        # background threads can't reliably open new DB connections.
        if not getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
            from apps.llm_ranking.tasks import run_llm_ranking_audit
            run_llm_ranking_audit.delay(audit_id=str(audit.id))

        return Response(
            LLMRankingAuditListSerializer(audit).data,
            status=status.HTTP_202_ACCEPTED,
        )


class ScanURLView(TenantScopedAPIView):
    """
    POST — scan a single URL and return extracted content preview.

    Used by the frontend to let users preview what will be extracted
    from a URL before adding it as audit context.
    """

    def post(self, request, website_id):
        self.get_website(website_id)
        url = request.data.get("url", "").strip()
        if not url:
            return Response(
                {"error": "url is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.llm_ranking.services.domain_scanner import scan_domain

        scan = scan_domain(url)
        return Response({
            "url": url,
            "success": scan["success"],
            "business_name": scan.get("business_name", ""),
            "description": scan.get("description", "")[:300],
            "products": scan.get("products", []),
            "features": scan.get("features", []),
            "selling_points": scan.get("selling_points", []),
            "content_summary": (scan.get("content_summary") or "")[:500],
            "error": scan.get("error"),
        })


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


class LLMRankingAuditRunView(TenantScopedAPIView):
    """
    POST — Run (or re-run) a pending/failed audit synchronously.
    Returns the updated audit when complete.
    """

    def post(self, request, website_id, audit_id):
        self.get_website(website_id)
        audit = self.get_tenant_object(
            LLMRankingAudit, id=audit_id, website_id=website_id,
        )
        if audit.status == LLMRankingAudit.STATUS_COMPLETED:
            return Response(
                {"error": "Audit already completed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if audit.status == LLMRankingAudit.STATUS_RUNNING:
            return Response(
                {"error": "Audit is already running."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Reset to pending and clear old results for re-runs
        if audit.status == LLMRankingAudit.STATUS_FAILED:
            audit.results.all().delete()
            audit.status = LLMRankingAudit.STATUS_PENDING
            audit.overall_score = 0
            audit.mention_rate = 0.0
            audit.queries_completed = 0
            audit.total_queries = 0
            audit.error_message = ""
            audit.save()

        # Run synchronously in the request thread
        from apps.llm_ranking.services.ranking_service import LLMRankingService
        try:
            LLMRankingService.run_audit(audit_id=str(audit.id))
        except Exception as exc:
            logger.error("LLM ranking audit %s failed: %s", audit.id, exc)
            LLMRankingAudit.objects.filter(id=audit.id).update(
                status=LLMRankingAudit.STATUS_FAILED,
                error_message=str(exc),
            )
            return Response(
                {"error": f"Audit failed: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Refresh and return
        audit.refresh_from_db()
        return Response(LLMRankingAuditListSerializer(audit).data)


class LLMRankingAuditLogsView(TenantScopedAPIView):
    """
    GET — return live pipeline logs for an audit.

    Used by the frontend to display real-time progress during a running audit.
    Supports ?after=<ISO8601> to only return new entries since the given timestamp.
    """

    def get(self, request, website_id, audit_id):
        self.get_website(website_id)
        audit = self.get_tenant_object(
            LLMRankingAudit, id=audit_id, website_id=website_id,
        )
        logs = list(audit.audit_logs or [])

        # Optional: only return logs after a given timestamp
        after = request.query_params.get("after")
        if after:
            logs = [l for l in logs if l.get("ts", "") > after]

        return Response({
            "audit_id": str(audit.id),
            "status": audit.status,
            "queries_completed": audit.queries_completed,
            "total_queries": audit.total_queries,
            "logs": logs,
        })

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


class LLMRankingPromptResultsView(TenantScopedAPIView):
    """
    GET — prompt-level aggregation for an audit.

    Query params:
      ?provider=claude   — filter to show only results from one LLM
      ?type=recommendation — filter by prompt type

    Groups LLMRankingResult rows by prompt text and returns per-provider
    metrics for each prompt.
    """

    def get(self, request, website_id, audit_id):
        from collections import OrderedDict

        self.get_website(website_id)
        audit = self.get_tenant_object(
            LLMRankingAudit.objects.prefetch_related("results"),
            id=audit_id,
            website_id=website_id,
        )

        # Optional filters
        filter_provider = request.query_params.get("provider", "").strip()
        filter_type = request.query_params.get("type", "").strip()

        # Build prompt type lookup from the audit's stored prompts
        prompt_type_map = {}
        for p in (audit.prompts or []):
            if isinstance(p, dict):
                prompt_type_map[p.get("text", "").strip().lower()] = p.get("type", "custom")

        # Group results by prompt text (preserving order)
        prompt_groups = OrderedDict()
        results_qs = audit.results.all().order_by("id")
        if filter_provider:
            results_qs = results_qs.filter(provider=filter_provider)

        for result in results_qs:
            key = result.prompt.strip()
            ptype = getattr(result, 'prompt_type', '') or prompt_type_map.get(key.lower(), "custom")

            # Filter by prompt type if requested
            if filter_type and ptype != filter_type:
                continue

            if key not in prompt_groups:
                prompt_groups[key] = {
                    "prompt": key,
                    "prompt_type": ptype,
                    "providers": {},
                    "total_providers": 0,
                    "mentioned_count": 0,
                    "succeeded_count": 0,
                }
            group = prompt_groups[key]
            group["total_providers"] += 1
            if result.query_succeeded:
                group["succeeded_count"] += 1
            if result.is_mentioned:
                group["mentioned_count"] += 1

            group["providers"][result.provider] = {
                "provider": result.provider,
                "provider_display": result.get_provider_display(),
                "mentioned": result.is_mentioned,
                "rank": result.mention_rank,
                "sentiment": result.sentiment,
                "sentiment_display": result.get_sentiment_display(),
                "confidence": result.confidence_score,
                "context": result.mention_context[:200] if result.mention_context else "",
                "is_linked": result.is_linked,
                "primary_recommendation": result.primary_recommendation,
                "competitors_mentioned": result.competitors_mentioned,
                "succeeded": result.query_succeeded,
                "error": result.error_message if not result.query_succeeded else "",
            }

        # Compute derived fields
        prompts_list = []
        for idx, (prompt_text, group) in enumerate(prompt_groups.items(), start=1):
            succeeded = group["succeeded_count"]
            mentioned = group["mentioned_count"]
            visibility = round(mentioned / succeeded * 100, 1) if succeeded else 0.0

            # Determine status
            expected = 1 if filter_provider else len(audit.providers_queried or [])
            if group["total_providers"] == 0:
                prompt_status = "pending"
            elif all(not p["succeeded"] for p in group["providers"].values()):
                prompt_status = "failed"
            elif group["total_providers"] < expected:
                prompt_status = "partial"
            else:
                prompt_status = "completed"

            prompts_list.append({
                "index": idx,
                "prompt": prompt_text,
                "prompt_type": group["prompt_type"],
                "avg_visibility": visibility,
                "mentioned_count": mentioned,
                "total_providers": succeeded,
                "providers": group["providers"],
                "status": prompt_status,
            })

        return Response({
            "audit_id": str(audit.id),
            "business_name": audit.business_name,
            "total_prompts": len(prompts_list),
            "providers_queried": audit.providers_queried,
            "filter_provider": filter_provider or None,
            "filter_type": filter_type or None,
            "prompts": prompts_list,
        })


class LLMRankingProviderDetailView(TenantScopedAPIView):
    """
    GET — detailed per-model report for a single provider in an audit.

    Returns every prompt result for the specified provider, plus aggregate
    metrics: visibility %, avg rank, sentiment breakdown, top competitors,
    and response quality stats.

    URL: .../audits/<audit_id>/providers/<provider>/
    """

    def get(self, request, website_id, audit_id, provider):
        from apps.llm_ranking.services.ranking_service import wilson_ci

        self.get_website(website_id)
        audit = self.get_tenant_object(
            LLMRankingAudit.objects.prefetch_related("results"),
            id=audit_id,
            website_id=website_id,
        )

        results = list(
            audit.results.filter(provider=provider).order_by("id")
        )
        if not results:
            return Response(
                {"error": f"No results found for provider '{provider}'."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Build prompt type lookup
        prompt_type_map = {}
        for p in (audit.prompts or []):
            if isinstance(p, dict):
                prompt_type_map[p.get("text", "").strip().lower()] = p.get("type", "custom")

        # Aggregate metrics
        succeeded = [r for r in results if r.query_succeeded]
        mentioned = [r for r in succeeded if r.is_mentioned]
        mention_rate = round(len(mentioned) / len(succeeded) * 100, 1) if succeeded else 0.0

        ci_low, ci_high = wilson_ci(len(mentioned), len(succeeded))

        ranks = [r.mention_rank for r in mentioned if r.mention_rank is not None]
        avg_rank = round(sum(ranks) / len(ranks), 1) if ranks else None

        # Sentiment breakdown
        sentiments = {"positive": 0, "neutral": 0, "negative": 0, "not_mentioned": 0}
        for r in succeeded:
            s = r.sentiment
            if s in sentiments:
                sentiments[s] += 1

        # Top competitors — collapse surface-form variants ("Mixpanel" /
        # "mixpanel" / "Mixpanel Inc.") so the leaderboard isn't inflated.
        from apps.llm_ranking.services.competitor_normalize import (
            canonical_name, MIN_MENTIONS_FOR_RANKING,
        )
        comp_counts: dict = {}
        for r in succeeded:
            for c in (r.competitors_mentioned or []):
                if not isinstance(c, dict):
                    continue
                raw = (c.get("name") or "").strip()
                key = canonical_name(raw)
                if not key:
                    continue
                bucket = comp_counts.setdefault(
                    key, {"display": raw, "mentions": 0}
                )
                bucket["mentions"] += 1
        top_competitors = sorted(
            [
                {"name": v["display"], "mentions": v["mentions"]}
                for v in comp_counts.values()
                if v["mentions"] >= MIN_MENTIONS_FOR_RANKING
            ],
            key=lambda x: x["mentions"], reverse=True,
        )[:10]

        # Per-prompt details
        prompt_details = []
        for idx, r in enumerate(results, start=1):
            prompt_details.append({
                "index": idx,
                "prompt": r.prompt,
                "prompt_type": getattr(r, 'prompt_type', '') or prompt_type_map.get(r.prompt.strip().lower(), "custom"),
                "succeeded": r.query_succeeded,
                "mentioned": r.is_mentioned,
                "rank": r.mention_rank,
                "sentiment": r.sentiment,
                "sentiment_display": r.get_sentiment_display(),
                "confidence": r.confidence_score,
                "context": r.mention_context[:300] if r.mention_context else "",
                "is_linked": r.is_linked,
                "primary_recommendation": r.primary_recommendation,
                "competitors_mentioned": r.competitors_mentioned,
                "citations": r.citations,
                "response_length": len(r.response_text) if r.response_text else 0,
                "error": r.error_message if not r.query_succeeded else "",
            })

        # Provider display name
        provider_display = results[0].get_provider_display() if results else provider

        return Response({
            "audit_id": str(audit.id),
            "business_name": audit.business_name,
            "provider": provider,
            "provider_display": provider_display,
            "summary": {
                "total_prompts": len(results),
                "succeeded": len(succeeded),
                "failed": len(results) - len(succeeded),
                "mentioned": len(mentioned),
                "mention_rate": mention_rate,
                "mention_rate_ci": [round(ci_low * 100, 1), round(ci_high * 100, 1)],
                "avg_rank": avg_rank,
                "sentiments": sentiments,
                "avg_confidence": round(
                    sum(r.confidence_score for r in succeeded) / len(succeeded), 1
                ) if succeeded else 0,
                "linked_count": sum(1 for r in mentioned if r.is_linked),
                "avg_response_length": round(
                    sum(len(r.response_text) for r in succeeded) / len(succeeded)
                ) if succeeded else 0,
            },
            "top_competitors": top_competitors,
            "prompts": prompt_details,
        })


class LLMRankingUsageView(TenantScopedAPIView):
    """
    GET — AI usage metrics for LLM ranking audits.

    Returns token consumption, costs, and call counts for the llm_ranking
    module, optionally filtered by website. Uses the existing AITokenUsage
    tracking infrastructure.

    Query params:
      ?days=30     — look-back period (default 30)
    """

    def get(self, request, website_id):
        self.get_website(website_id)
        days = int(request.query_params.get("days", 30))

        try:
            from apps.accounts.models import AITokenUsage
        except ImportError:
            return Response({"error": "Usage tracking not available."}, status=500)

        cutoff = timezone.now() - timedelta(days=days)
        # Tenant safety: scope every llm_ranking AITokenUsage row by the
        # current website AND the requesting user. The OR-with-website-isnull
        # workaround that used to be here leaked website-less rows from any
        # tenant; now that extraction/context calls all pass website through,
        # an exact website match is correct.
        qs = AITokenUsage.objects.filter(
            module="llm_ranking",
            created_at__gte=cutoff,
            website_id=website_id,
            user=request.user,
        )

        # Overall totals
        from django.db.models import Sum
        from django.db.models.functions import TruncDate

        totals = qs.aggregate(
            total_calls=Count("id"),
            total_input=Sum("input_tokens"),
            total_output=Sum("output_tokens"),
            total_tokens=Sum("total_tokens"),
            total_cost=Sum("estimated_cost_usd"),
        )

        # Per-model breakdown
        by_model = list(
            qs.values("model_name").annotate(
                calls=Count("id"),
                input_tokens=Sum("input_tokens"),
                output_tokens=Sum("output_tokens"),
                tokens=Sum("total_tokens"),
                cost=Sum("estimated_cost_usd"),
            ).order_by("-tokens")
        )

        # Daily trend
        daily = list(
            qs.annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(
                calls=Count("id"),
                tokens=Sum("total_tokens"),
                cost=Sum("estimated_cost_usd"),
            )
            .order_by("day")
        )

        # Audit-level usage: count audits and prompts
        audit_stats = LLMRankingAudit.objects.filter(
            website_id=website_id,
            created_at__gte=cutoff,
        ).aggregate(
            total_audits=Count("id"),
            completed_audits=Count("id", filter=Q(status="completed")),
            total_queries=Sum("total_queries"),
        )

        return Response({
            "period_days": days,
            "totals": {
                "calls": totals["total_calls"] or 0,
                "input_tokens": totals["total_input"] or 0,
                "output_tokens": totals["total_output"] or 0,
                "total_tokens": totals["total_tokens"] or 0,
                "estimated_cost_usd": round(float(totals["total_cost"] or 0), 4),
            },
            "audit_stats": {
                "total_audits": audit_stats["total_audits"] or 0,
                "completed_audits": audit_stats["completed_audits"] or 0,
                "total_queries_run": audit_stats["total_queries"] or 0,
            },
            "by_model": by_model,
            "daily": daily,
        })


class LLMRankingProviderHealthView(TenantScopedAPIView):
    """
    GET — list every provider the ranking module can actually call, with its
    canonical key, label, model, and configured status (API key present).

    Stub providers (Meta Llama, Mistral, Cohere, etc.) listed in the model
    schema but lacking an implementation are deliberately excluded so the UI
    can never queue a run that would silently produce no results.
    """

    def get(self, request, website_id):
        self.get_website(website_id)
        from apps.llm_ranking.providers import PROVIDERS

        labels = {
            "claude": "Claude",
            "gpt4": "GPT-4",
            "gemini": "Gemini",
            "perplexity": "Perplexity",
        }
        items = []
        for key, cls in PROVIDERS.items():
            configured = bool(getattr(settings, cls.api_key_setting, ""))
            items.append({
                "key": key,
                "name": labels.get(key, key),
                "model": cls.model,
                "api_key_setting": cls.api_key_setting,
                "configured": configured,
            })
        return Response({
            "providers": items,
            "configured_count": sum(1 for p in items if p["configured"]),
            "total": len(items),
        })


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
        # JSONField list[dict] so we iterate in Python. Surface-form variants
        # ("Mixpanel" / "mixpanel" / "Mixpanel Inc.") are collapsed via
        # canonical_name() so the citation-share denominator and rankings
        # aren't inflated by name drift.
        from apps.llm_ranking.services.competitor_normalize import (
            canonical_name, MIN_MENTIONS_FOR_RANKING,
        )
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
            self_mention = 1 if r["is_mentioned"] else 0
            per_audit_self_brand_mentions[aid] = (
                per_audit_self_brand_mentions.get(aid, 0) + self_mention
            )

            # Dedupe by canonical key within a single response so naming the
            # same brand twice doesn't double-count the citation-share total.
            seen_canonical: set = set()
            unique_competitor_count_in_response = 0
            for c in comps:
                if not isinstance(c, dict):
                    continue
                raw = (c.get("name") or "").strip()
                key = canonical_name(raw)
                if not key or key in seen_canonical:
                    continue
                seen_canonical.add(key)
                unique_competitor_count_in_response += 1

                bucket_key = (aid, key)
                bucket = competitor_by_audit.setdefault(
                    bucket_key, {"display": raw, "count": 0, "ranks": []},
                )
                bucket["count"] += 1
                pos = c.get("position")
                if isinstance(pos, (int, float)) and pos is not None:
                    bucket["ranks"].append(int(pos))

            per_audit_total_brand_mentions[aid] = (
                per_audit_total_brand_mentions.get(aid, 0)
                + self_mention
                + unique_competitor_count_in_response
            )

        # Group into per-audit lists, applying the min-mentions threshold.
        comp_list_by_audit: dict = {}
        for (aid, _key), v in competitor_by_audit.items():
            if v["count"] < MIN_MENTIONS_FOR_RANKING:
                continue
            total_prompts = max(per_audit_total.get(aid, 0), 1)
            visibility = round(v["count"] / total_prompts * 100, 1)
            avg_rank = (
                round(sum(v["ranks"]) / len(v["ranks"]), 1)
                if v["ranks"] else None
            )
            comp_list_by_audit.setdefault(aid, []).append({
                "name": v["display"],
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
