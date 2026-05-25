"""API tests for the Sources > URLs dashboard endpoints."""
import pytest
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

pytestmark = pytest.mark.django_db


@pytest.fixture
def auth_client():
    user = UserFactory()
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


def _seed(user):
    website = WebsiteFactory(user=user)
    audit = LLMRankingAuditFactory(website=website, created_by=user)
    result = LLMRankingResultFactory(
        audit=audit,
        provider=LLMRankingResult.PROVIDER_PERPLEXITY,
        prompt_index=0,
        prompt="best treasury management software",
        citations=[
            {"url": "https://reddit.com/r/saas"},
            {"url": "https://techcrunch.com/x"},
        ],
        response_text="Some answer text.",
    )
    extract_for_result(str(result.id))
    return website, audit, result


class TestWebsiteUrls:
    def test_requires_auth(self):
        website = WebsiteFactory()
        client = APIClient()
        url = reverse("citations-website-urls", args=[website.id])
        assert client.get(url).status_code == 401

    def test_empty_website(self, auth_client):
        client, user = auth_client
        website = WebsiteFactory(user=user)
        url = reverse("citations-website-urls", args=[website.id])
        resp = client.get(url)
        assert resp.status_code == 200
        assert resp.data["total_retrievals"] == 0
        assert resp.data["unique_urls"] == 0
        assert resp.data["urls"] == []
        assert resp.data["url_types"] == []
        assert resp.data["movers"]["Top"] == []

    def test_aggregates_urls(self, auth_client):
        client, user = auth_client
        website, audit, _ = _seed(user)
        r2 = LLMRankingResultFactory(
            audit=audit, provider=LLMRankingResult.PROVIDER_CLAUDE, prompt_index=1,
            prompt="top treasury tools", citations=[{"url": "https://reddit.com/r/saas"}],
            response_text="",
        )
        extract_for_result(str(r2.id))

        url = reverse("citations-website-urls", args=[website.id])
        resp = client.get(url)
        assert resp.status_code == 200
        body = resp.data
        assert body["total_retrievals"] == 3
        assert body["unique_urls"] == 2
        rows = {r["apex_domain"]: r for r in body["urls"]}
        assert rows["reddit.com"]["retrievals"] == 2
        assert set(rows["reddit.com"]["models"]) == {"perplexity", "claude"}
        assert rows["reddit.com"]["domain_type"] == "UGC"
        assert body["urls"][0]["retrievals"] >= body["urls"][1]["retrievals"]
        assert sum(t["count"] for t in body["url_types"]) == 3
        assert body["overview"]["series"]

    def test_tenant_isolation(self, auth_client):
        client, _ = auth_client
        other = UserFactory()
        other_website = WebsiteFactory(user=other)
        url = reverse("citations-website-urls", args=[other_website.id])
        assert client.get(url).status_code in (403, 404)


class TestWebsiteUrlDetail:
    def test_missing_url_param(self, auth_client):
        client, user = auth_client
        website = WebsiteFactory(user=user)
        url = reverse("citations-website-url-detail", args=[website.id])
        assert client.get(url).status_code == 400

    def test_unknown_url_404(self, auth_client):
        client, user = auth_client
        website, _, _ = _seed(user)
        url = reverse("citations-website-url-detail", args=[website.id])
        resp = client.get(url, {"url": "https://nope.example.com/x"})
        assert resp.status_code == 404

    def test_detail_payload(self, auth_client):
        client, user = auth_client
        website, audit, _ = _seed(user)
        url = reverse("citations-website-url-detail", args=[website.id])
        resp = client.get(url, {"url": "https://reddit.com/r/saas"})
        assert resp.status_code == 200
        body = resp.data
        assert body["metrics"]["retrievals"]["value"] == 1
        assert body["metrics"]["domain_type"] == "UGC"
        assert "labels" in body["retrievals_over_time"]
        assert any(m["model"] == "perplexity" for m in body["retrievals_by_model"])
        assert len(body["prompts"]) == 1
        assert isinstance(body["chats"], list)
