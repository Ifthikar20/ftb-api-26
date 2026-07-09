"""REST endpoints for Brand Security.

Live under ``/api/v1/brand-security/``. The legacy ``/brand-vault/safety/*``
endpoints in ``views.py`` stay in place for a release so existing UI clients
keep working while we migrate. Prefer these views for new work.
"""
from __future__ import annotations

from collections import Counter

from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from apps.brand_vault.api.v1.serializers import (
    BrandSecurityAgentPatchSerializer,
    BrandSecurityAgentSerializer,
    BrandSecurityConfigSerializer,
    SafetyAlertSerializer,
    SafetyPromptCreateSerializer,
    SafetyPromptSerializer,
)
from apps.brand_vault.models import (
    BrandSecurityAgent,
    BrandSecurityConfig,
    SafetyAlert,
    SafetyPrompt,
)
from apps.brand_vault.services.security.orchestrator import (
    ensure_agent_rows,
    run_agent,
    run_all_agents,
)
from apps.brand_vault.services.security.registry import AGENTS, agent_catalog
from core.exceptions import ResourceNotFound
from core.views import TenantScopedAPIView, TenantScopedListAPIView

_SEVERITY_WEIGHTS = {
    SafetyAlert.SEVERITY_HIGH: 10,
    SafetyAlert.SEVERITY_MEDIUM: 4,
    SafetyAlert.SEVERITY_LOW: 1,
}


class BrandSecurityOverviewView(TenantScopedAPIView):
    """Top-of-page summary tiles: health, counters, and last-scan timing."""

    def get(self, request, website_id):
        website = self.get_website(website_id)
        open_alerts = SafetyAlert.objects.filter(
            website=website, status=SafetyAlert.STATUS_OPEN,
        )

        by_severity = Counter(open_alerts.values_list("severity", flat=True))
        penalty = sum(
            _SEVERITY_WEIGHTS.get(sev, 0) * n
            for sev, n in by_severity.items()
        )
        health = max(0, min(100, 100 - penalty))

        by_source = Counter(open_alerts.values_list("source", flat=True))
        by_agent = Counter(open_alerts.values_list("agent_id", flat=True))

        agents = ensure_agent_rows(website)
        last_run_at = max(
            (a.last_run_at for a in agents if a.last_run_at),
            default=None,
        )
        next_run_at = min(
            (a.next_run_at for a in agents if a.next_run_at),
            default=None,
        )

        return Response({
            "health_score": health,
            "open_alerts": open_alerts.count(),
            "by_severity": {
                "high": by_severity.get(SafetyAlert.SEVERITY_HIGH, 0),
                "medium": by_severity.get(SafetyAlert.SEVERITY_MEDIUM, 0),
                "low": by_severity.get(SafetyAlert.SEVERITY_LOW, 0),
            },
            "by_source": dict(by_source),
            "by_agent": dict(by_agent),
            "last_run_at": last_run_at,
            "next_run_at": next_run_at,
            "prompts_monitored": SafetyPrompt.objects.filter(
                website=website, status=SafetyPrompt.STATUS_ACTIVE,
            ).count(),
        })


class BrandSecurityAgentsView(TenantScopedAPIView):
    """List every registered agent with its per-website state."""

    def get(self, request, website_id):
        website = self.get_website(website_id)
        ensure_agent_rows(website)

        catalog = {row["agent_id"]: row for row in agent_catalog()}
        rows = list(
            BrandSecurityAgent.objects.filter(website=website).order_by("agent_id"),
        )

        # One aggregation query for open-alert counts by (agent, severity).
        counts = (
            SafetyAlert.objects.filter(
                website=website, status=SafetyAlert.STATUS_OPEN,
            )
            .values("agent_id", "severity")
            .annotate(n=Count("id"))
        )
        agg: dict[str, dict[str, int]] = {}
        for c in counts:
            agg.setdefault(c["agent_id"], {})[c["severity"]] = c["n"]

        payload = []
        for row in rows:
            meta = catalog.get(row.agent_id, {})
            by_sev = agg.get(row.agent_id, {})
            row.display_name = meta.get("display_name", row.agent_id)
            row.tagline = meta.get("tagline", "")
            row.color = meta.get("color", "slate")
            row.sources = meta.get("sources", [])
            row.open_high = by_sev.get(SafetyAlert.SEVERITY_HIGH, 0)
            row.open_medium = by_sev.get(SafetyAlert.SEVERITY_MEDIUM, 0)
            row.open_low = by_sev.get(SafetyAlert.SEVERITY_LOW, 0)
            row.open_alerts = row.open_high + row.open_medium + row.open_low
            payload.append(BrandSecurityAgentSerializer(row).data)

        return Response(payload)


class BrandSecurityAgentDetailView(TenantScopedAPIView):
    """PATCH an agent's config or POST to run it now."""

    def _get(self, request, website_id, agent_id) -> BrandSecurityAgent:
        website = self.get_website(website_id)
        try:
            row = BrandSecurityAgent.objects.get(
                website=website, agent_id=agent_id,
            )
        except BrandSecurityAgent.DoesNotExist as exc:
            raise ResourceNotFound("Agent not found.") from exc
        return row

    def patch(self, request, website_id, agent_id):
        row = self._get(request, website_id, agent_id)
        ser = BrandSecurityAgentPatchSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        for field, value in ser.validated_data.items():
            setattr(row, field, value)
        row.save()
        return Response(BrandSecurityAgentSerializer(row).data)


class BrandSecurityAgentRunView(TenantScopedAPIView):
    """Run one agent on demand."""

    def post(self, request, website_id, agent_id):
        website = self.get_website(website_id)
        if agent_id not in AGENTS:
            raise ResourceNotFound("Agent not found.")
        result = run_agent(website, agent_id)
        return Response(result)


class BrandSecurityScanView(TenantScopedAPIView):
    """Run every enabled agent for this website."""

    def post(self, request, website_id):
        website = self.get_website(website_id)
        only = request.data.get("only") if isinstance(request.data, dict) else None
        if only is not None and not isinstance(only, list):
            only = None
        result = run_all_agents(website, only=only)
        return Response(result)


class BrandSecurityAlertsView(TenantScopedListAPIView):
    """List alerts filterable by agent, severity, source, issue, status."""

    def get(self, request, website_id):
        website = self.get_website(website_id)
        qs = SafetyAlert.objects.filter(website=website)

        agent_ids = request.query_params.getlist("agent_id")
        if agent_ids:
            qs = qs.filter(agent_id__in=agent_ids)
        severities = request.query_params.getlist("severity")
        if severities:
            qs = qs.filter(severity__in=severities)
        sources = request.query_params.getlist("source")
        if sources:
            qs = qs.filter(source__in=sources)
        issues = request.query_params.getlist("issue")
        if issues:
            qs = qs.filter(issue__in=issues)
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        qs = qs.order_by("-detected_at")
        return self.paginated_response(qs, SafetyAlertSerializer)


class BrandSecurityAlertActionView(TenantScopedAPIView):
    """Resolve or dismiss an alert."""

    def post(self, request, alert_id, action):
        try:
            alert = SafetyAlert.objects.select_related("website").get(id=alert_id)
        except SafetyAlert.DoesNotExist as exc:
            raise ResourceNotFound("Alert not found.") from exc
        self.get_website(alert.website_id)

        if action == "dismiss":
            alert.status = SafetyAlert.STATUS_DISMISSED
        elif action == "resolve":
            alert.status = SafetyAlert.STATUS_RESOLVED
        else:
            return Response(
                {"error": "Unknown action."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        alert.resolved_at = timezone.now()
        alert.resolved_by = request.user
        alert.save(update_fields=["status", "resolved_at", "resolved_by", "updated_at"])
        return Response(SafetyAlertSerializer(alert).data)


class BrandSecurityConfigView(TenantScopedAPIView):
    """Read or update the per-website brand terms + negative keywords."""

    def get(self, request, website_id):
        website = self.get_website(website_id)
        cfg, _ = BrandSecurityConfig.objects.get_or_create(website=website)
        return Response(BrandSecurityConfigSerializer(cfg).data)

    def put(self, request, website_id):
        website = self.get_website(website_id)
        cfg, _ = BrandSecurityConfig.objects.get_or_create(website=website)
        terms = request.data.get("brand_terms")
        if isinstance(terms, list):
            cfg.brand_terms = [str(x).strip() for x in terms if str(x).strip()]
        negatives = request.data.get("negative_keywords")
        if isinstance(negatives, list):
            cfg.negative_keywords = [
                str(x).strip() for x in negatives if str(x).strip()
            ]
        cfg.save()
        return Response(BrandSecurityConfigSerializer(cfg).data)


class BrandSecurityPromptsView(TenantScopedListAPIView):
    """List or create SafetyPrompts (used by LLM Truth)."""

    def get(self, request, website_id):
        website = self.get_website(website_id)
        qs = SafetyPrompt.objects.filter(website=website).order_by("-created_at")
        return self.paginated_response(qs, SafetyPromptSerializer)

    def post(self, request, website_id):
        website = self.get_website(website_id)
        ser = SafetyPromptCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        text = ser.validated_data["text"].strip()
        prompt, created = SafetyPrompt.objects.get_or_create(
            website=website, text=text,
            defaults={"created_by": request.user},
        )
        return Response(
            SafetyPromptSerializer(prompt).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class BrandSecurityPromptDetailView(TenantScopedAPIView):
    """Delete a SafetyPrompt."""

    def delete(self, request, prompt_id):
        try:
            prompt = SafetyPrompt.objects.select_related("website").get(id=prompt_id)
        except SafetyPrompt.DoesNotExist as exc:
            raise ResourceNotFound("Prompt not found.") from exc
        self.get_website(prompt.website_id)
        prompt.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
