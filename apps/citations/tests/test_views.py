"""API tests for the citations endpoints."""
import pytest
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.citations.services.extraction_service import extract_for_result
from apps.llm_ranking.models import LLMRankingResult
from apps.llm_ranking.tests.factories import (
    LLMRankingAuditFactory,
    LLMRankingResultFactory,
)
from apps.websites.tests.factories import WebsiteFactory

pytestmark = [pytest.mark.django_db, override_settings(CITATION_EXTRACTION_ENABLED=False)]


@pytest.fixture
def auth_client():
    user = UserFactory()
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


def _seed_audit_with_citations(user):
    website = WebsiteFactory(user=user)
    audit = LLMRankingAuditFactory(website=website, created_by=user)
    result = LLMRankingResultFactory(
        audit=audit,
        provider=LLMRankingResult.PROVIDER_PERPLEXITY,
        prompt_index=0,
        citations=[
            {"url": "https://reddit.com/r/saas"},
            {"url": "https://techcrunch.com/x"},
        ],
        response_text="",
    )
    extract_for_result(str(result.id))
    return website, audit, result


class TestAuthGuard:
    def test_audit_citations_requires_auth(self):
        audit = LLMRankingAuditFactory()
        client = APIClient()
        url = reverse("citations-audit-list", args=[audit.id])
        resp = client.get(url)
        assert resp.status_code == 401


class TestAuditCitations:
    def test_lists_for_owner(self, auth_client):
        client, user = auth_client
        _, audit, _ = _seed_audit_with_citations(user)
        url = reverse("citations-audit-list", args=[audit.id])
        resp = client.get(url)
        assert resp.status_code == 200
        results = resp.data["results"] if "results" in resp.data else resp.data
        assert len(results) == 2

    def test_filter_by_source_class(self, auth_client):
        client, user = auth_client
        _, audit, _ = _seed_audit_with_citations(user)
        url = reverse("citations-audit-list", args=[audit.id])
        resp = client.get(url, {"source_class": "reddit"})
        results = resp.data["results"] if "results" in resp.data else resp.data
        assert len(results) == 1
        assert results[0]["source_class"] == "reddit"

    def test_tenant_isolation(self, auth_client):
        client, user = auth_client
        # Audit belongs to a *different* user.
        other = UserFactory()
        _, audit, _ = _seed_audit_with_citations(other)
        url = reverse("citations-audit-list", args=[audit.id])
        resp = client.get(url)
        assert resp.status_code in (403, 404)


class TestAuditSourceInfluence:
    def test_returns_provider_breakdown(self, auth_client):
        client, user = auth_client
        _, audit, _ = _seed_audit_with_citations(user)
        url = reverse("citations-audit-influence", args=[audit.id])
        resp = client.get(url)
        assert resp.status_code == 200
        assert resp.data["total_citations"] == 2
        assert "perplexity" in resp.data["providers"]


class TestWebsiteCitationsAndInfluence:
    def test_website_citations_list(self, auth_client):
        client, user = auth_client
        website, _, _ = _seed_audit_with_citations(user)
        url = reverse("citations-website-list", args=[website.id])
        resp = client.get(url)
        assert resp.status_code == 200
        results = resp.data["results"] if "results" in resp.data else resp.data
        assert len(results) == 2

    def test_website_influence_empty(self, auth_client):
        client, user = auth_client
        website = WebsiteFactory(user=user)
        url = reverse("citations-website-influence", args=[website.id])
        resp = client.get(url)
        assert resp.status_code == 200
        assert resp.data["snapshots"] == []


class TestGlobalInfluence:
    def test_returns_snapshots_payload(self, auth_client):
        client, _ = auth_client
        url = reverse("citations-global-influence")
        resp = client.get(url)
        assert resp.status_code == 200
        assert "snapshots" in resp.data
        assert "source_classes" in resp.data
