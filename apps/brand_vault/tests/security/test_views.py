"""API contract tests for the /api/v1/brand-security/ endpoints."""
from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.brand_vault.models import (
    BrandSecurityAgent,
    BrandSecurityConfig,
    SafetyAlert,
    SafetyPrompt,
)
from apps.websites.tests.factories import WebsiteFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def auth():
    user = UserFactory()
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


def _make_alert(website, **kwargs):
    defaults = dict(
        website=website,
        agent_id="llm_truth",
        source=SafetyAlert.SOURCE_LLM,
        title="Is Acme legit?",
        snippet="Acme is a scam.",
        issue=SafetyAlert.ISSUE_HALLUCINATION,
        severity=SafetyAlert.SEVERITY_HIGH,
        model="claude",
        prompt_text="Is Acme legit?",
    )
    defaults.update(kwargs)
    return SafetyAlert.objects.create(**defaults)


class TestOverview:
    def test_requires_auth(self):
        website = WebsiteFactory()
        url = reverse("brand-security-overview", args=[website.id])
        assert APIClient().get(url).status_code == 401

    def test_returns_health_and_counters(self, auth):
        client, user = auth
        website = WebsiteFactory(user=user)
        _make_alert(website, severity="high")
        _make_alert(website, severity="medium",
                    agent_id="serp_reputation", source=SafetyAlert.SOURCE_SERP)
        SafetyPrompt.objects.create(website=website, text="Is Acme legit?")

        resp = client.get(reverse("brand-security-overview", args=[website.id]))
        assert resp.status_code == 200
        body = resp.data
        assert body["open_alerts"] == 2
        assert body["by_severity"]["high"] == 1
        assert body["by_severity"]["medium"] == 1
        # Health = 100 - (10*1 + 4*1) = 86
        assert body["health_score"] == 86
        assert body["prompts_monitored"] == 1
        assert body["by_agent"]["llm_truth"] == 1
        assert body["by_agent"]["serp_reputation"] == 1


class TestAgentsList:
    def test_seeds_agent_rows_on_first_call(self, auth):
        client, user = auth
        website = WebsiteFactory(user=user)
        assert BrandSecurityAgent.objects.filter(website=website).count() == 0
        resp = client.get(reverse("brand-security-agents", args=[website.id]))
        assert resp.status_code == 200
        assert len(resp.data) == 5  # 5 v1 agents
        names = {row["agent_id"] for row in resp.data}
        assert "llm_truth" in names
        assert "narrative_watch" in names
        assert BrandSecurityAgent.objects.filter(website=website).count() == 5

    def test_reports_open_alert_counts_per_agent(self, auth):
        client, user = auth
        website = WebsiteFactory(user=user)
        _make_alert(website, agent_id="llm_truth", severity="high")
        _make_alert(website, agent_id="llm_truth", severity="low",
                    title="Different")

        resp = client.get(reverse("brand-security-agents", args=[website.id]))
        row = next(r for r in resp.data if r["agent_id"] == "llm_truth")
        assert row["open_alerts"] == 2
        assert row["open_high"] == 1
        assert row["open_low"] == 1


class TestAgentPatchAndRun:
    def test_patch_updates_sensitivity(self, auth):
        client, user = auth
        website = WebsiteFactory(user=user)
        BrandSecurityAgent.objects.create(
            website=website, agent_id="llm_truth", sensitivity="medium",
        )
        url = reverse(
            "brand-security-agent-detail",
            kwargs={"website_id": website.id, "agent_id": "llm_truth"},
        )
        resp = client.patch(url, {"sensitivity": "high", "enabled": False}, format="json")
        assert resp.status_code == 200
        row = BrandSecurityAgent.objects.get(website=website, agent_id="llm_truth")
        assert row.sensitivity == "high"
        assert row.enabled is False

    def test_run_endpoint_returns_stats(self, auth, monkeypatch):
        client, user = auth
        website = WebsiteFactory(user=user)
        BrandSecurityAgent.objects.create(
            website=website, agent_id="llm_truth", enabled=True,
        )
        from apps.brand_vault.services.security.registry import AGENTS
        monkeypatch.setattr(
            AGENTS["llm_truth"], "scan", lambda self, w, r: [],
        )
        url = reverse(
            "brand-security-agent-run",
            kwargs={"website_id": website.id, "agent_id": "llm_truth"},
        )
        resp = client.post(url)
        assert resp.status_code == 200
        assert resp.data["agent_id"] == "llm_truth"
        assert resp.data["alerts"] == 0


class TestAlerts:
    def test_filter_by_agent(self, auth):
        client, user = auth
        website = WebsiteFactory(user=user)
        _make_alert(website, agent_id="llm_truth")
        _make_alert(website, agent_id="serp_reputation",
                    source=SafetyAlert.SOURCE_SERP, title="X")
        url = reverse("brand-security-alerts", args=[website.id])
        resp = client.get(f"{url}?agent_id=llm_truth")
        results = resp.data.get("results", resp.data)
        assert len(results) == 1
        assert results[0]["agent_id"] == "llm_truth"

    def test_resolve_marks_alert(self, auth):
        client, user = auth
        website = WebsiteFactory(user=user)
        alert = _make_alert(website)
        url = reverse(
            "brand-security-alert-action",
            kwargs={"alert_id": alert.id, "action": "resolve"},
        )
        resp = client.post(url)
        assert resp.status_code == 200
        alert.refresh_from_db()
        assert alert.status == SafetyAlert.STATUS_RESOLVED
        assert alert.resolved_by_id == user.id


class TestConfig:
    def test_get_creates_config_lazily(self, auth):
        client, user = auth
        website = WebsiteFactory(user=user)
        url = reverse("brand-security-config", args=[website.id])
        resp = client.get(url)
        assert resp.status_code == 200
        assert BrandSecurityConfig.objects.filter(website=website).exists()

    def test_put_writes_terms(self, auth):
        client, user = auth
        website = WebsiteFactory(user=user)
        url = reverse("brand-security-config", args=[website.id])
        resp = client.put(
            url,
            {"brand_terms": ["Acme", "acme.io"], "negative_keywords": ["scam"]},
            format="json",
        )
        assert resp.status_code == 200
        cfg = BrandSecurityConfig.objects.get(website=website)
        assert cfg.brand_terms == ["Acme", "acme.io"]
        assert cfg.negative_keywords == ["scam"]


class TestScanQueue:
    def test_scan_returns_202_and_stamps_rows_queued(self, auth, monkeypatch):
        client, user = auth
        website = WebsiteFactory(user=user)
        captured = {}

        from apps.brand_vault import tasks

        monkeypatch.setattr(
            tasks.run_security_scan, "delay",
            lambda **kwargs: captured.update(kwargs),
        )

        resp = client.post(
            reverse("brand-security-scan", args=[website.id]), {}, format="json",
        )
        assert resp.status_code == 202
        assert resp.data["queued"] is True

        from apps.brand_vault.services.security.registry import AGENTS

        assert set(resp.data["agents"]) == set(AGENTS)
        assert captured["website_id"] == str(website.id)

        statuses = set(
            BrandSecurityAgent.objects.filter(website=website)
            .values_list("last_status", flat=True),
        )
        assert statuses == {BrandSecurityAgent.STATUS_QUEUED}

    def test_scan_with_all_agents_disabled_does_not_queue(self, auth, monkeypatch):
        client, user = auth
        website = WebsiteFactory(user=user)

        from apps.brand_vault.services.security.orchestrator import ensure_agent_rows

        ensure_agent_rows(website)
        BrandSecurityAgent.objects.filter(website=website).update(enabled=False)

        from apps.brand_vault import tasks

        calls = []
        monkeypatch.setattr(
            tasks.run_security_scan, "delay",
            lambda **kwargs: calls.append(kwargs),
        )

        resp = client.post(
            reverse("brand-security-scan", args=[website.id]), {}, format="json",
        )
        assert resp.status_code == 200
        assert resp.data["queued"] is False
        assert calls == []

    def test_scan_only_filters_queued_agents(self, auth, monkeypatch):
        client, user = auth
        website = WebsiteFactory(user=user)

        from apps.brand_vault import tasks

        captured = {}
        monkeypatch.setattr(
            tasks.run_security_scan, "delay",
            lambda **kwargs: captured.update(kwargs),
        )

        resp = client.post(
            reverse("brand-security-scan", args=[website.id]),
            {"only": ["llm_truth"]}, format="json",
        )
        assert resp.status_code == 202
        assert resp.data["agents"] == ["llm_truth"]
        assert captured["only"] == ["llm_truth"]
        queued = BrandSecurityAgent.objects.filter(
            website=website, last_status=BrandSecurityAgent.STATUS_QUEUED,
        )
        assert [row.agent_id for row in queued] == ["llm_truth"]


class TestScanStatus:
    def test_running_true_while_rows_queued(self, auth):
        client, user = auth
        website = WebsiteFactory(user=user)
        BrandSecurityAgent.objects.create(
            website=website, agent_id="llm_truth", enabled=True,
            last_status=BrandSecurityAgent.STATUS_QUEUED,
        )
        resp = client.get(
            reverse("brand-security-scan-status", args=[website.id]),
        )
        assert resp.status_code == 200
        assert resp.data["running"] is True
        assert resp.data["agents_running"] == ["llm_truth"]

    def test_idle_rows_report_not_running_and_count_open_alerts(self, auth):
        client, user = auth
        website = WebsiteFactory(user=user)
        BrandSecurityAgent.objects.create(
            website=website, agent_id="llm_truth", enabled=True,
            last_status=BrandSecurityAgent.STATUS_IDLE,
        )
        _make_alert(website)
        _make_alert(website, status=SafetyAlert.STATUS_RESOLVED)

        resp = client.get(
            reverse("brand-security-scan-status", args=[website.id]),
        )
        assert resp.status_code == 200
        assert resp.data["running"] is False
        assert resp.data["agents_running"] == []
        assert resp.data["open_alerts"] == 1

    def test_stale_running_rows_are_treated_as_finished(self, auth):
        from datetime import timedelta

        from django.utils import timezone

        client, user = auth
        website = WebsiteFactory(user=user)
        row = BrandSecurityAgent.objects.create(
            website=website, agent_id="llm_truth", enabled=True,
            last_status=BrandSecurityAgent.STATUS_RUNNING,
        )
        BrandSecurityAgent.objects.filter(pk=row.pk).update(
            updated_at=timezone.now() - timedelta(minutes=30),
        )
        resp = client.get(
            reverse("brand-security-scan-status", args=[website.id]),
        )
        assert resp.status_code == 200
        assert resp.data["running"] is False
