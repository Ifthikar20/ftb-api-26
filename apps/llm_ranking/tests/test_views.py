"""Tests for LLM Ranking API views."""
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.leads.tests.factories import WebsiteFactory
from apps.llm_ranking.models import LLMRankingAudit
from apps.llm_ranking.tests.factories import LLMRankingAuditFactory, LLMRankingResultFactory


@pytest.fixture
def auth_client():
    user = UserFactory()
    website = WebsiteFactory(user=user)
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user, website


@pytest.mark.django_db
class TestLLMRankingAuditListView:
    def test_list_empty(self, auth_client):
        client, user, website = auth_client
        response = client.get(f"/api/v1/llm-ranking/{website.id}/audits/")
        assert response.status_code == 200
        assert response.json()["data"]["count"] == 0

    def test_list_returns_audits(self, auth_client):
        client, user, website = auth_client
        LLMRankingAuditFactory(website=website, created_by=user)
        LLMRankingAuditFactory(website=website, created_by=user)
        response = client.get(f"/api/v1/llm-ranking/{website.id}/audits/")
        assert response.status_code == 200
        assert response.json()["data"]["count"] == 2

    def test_list_excludes_other_websites(self, auth_client):
        client, user, website = auth_client
        other_website = WebsiteFactory()
        LLMRankingAuditFactory(website=other_website)
        LLMRankingAuditFactory(website=website, created_by=user)
        response = client.get(f"/api/v1/llm-ranking/{website.id}/audits/")
        assert response.json()["data"]["count"] == 1

    def test_create_audit_queues_task(self, auth_client):
        client, user, website = auth_client
        with patch("apps.llm_ranking.tasks.run_llm_ranking_audit.delay") as mock_task, \
             patch("apps.llm_ranking.services.ranking_service.LLMRankingService.generate_prompts",
                   return_value=["What is the best SaaS tool?"]):
            response = client.post(
                f"/api/v1/llm-ranking/{website.id}/audits/",
                {
                    "business_name": "Acme SaaS",
                    "industry": "SaaS",
                    "keywords": ["analytics", "dashboard"],
                    "business_description": "Growth analytics platform",
                },
                format="json",
            )
        assert response.status_code == 202
        data = response.json()["data"]
        assert data["business_name"] == "Acme SaaS"
        assert data["status"] == "pending"
        mock_task.assert_called_once()

    def test_create_audit_with_custom_prompts(self, auth_client):
        client, user, website = auth_client
        with patch("apps.llm_ranking.tasks.run_llm_ranking_audit.delay"):
            response = client.post(
                f"/api/v1/llm-ranking/{website.id}/audits/",
                {
                    "business_name": "Acme SaaS",
                    "industry": "SaaS",
                    "custom_prompts": ["Find me a SaaS tool", "Best analytics software?"],
                },
                format="json",
            )
        assert response.status_code == 202
        # Verify prompts were stored
        audit_id = response.json()["data"]["id"]
        audit = LLMRankingAudit.objects.get(id=audit_id)
        assert "Find me a SaaS tool" in audit.prompts

    def test_create_audit_unauthenticated(self, auth_client):
        _, _, website = auth_client
        anon = APIClient()
        response = anon.post(f"/api/v1/llm-ranking/{website.id}/audits/", {})
        assert response.status_code == 401

    def test_create_audit_missing_required_fields(self, auth_client):
        client, user, website = auth_client
        response = client.post(
            f"/api/v1/llm-ranking/{website.id}/audits/",
            {"industry": "SaaS"},  # missing business_name
            format="json",
        )
        assert response.status_code == 400


@pytest.mark.django_db
class TestLLMRankingAuditDetailView:
    def test_get_audit_with_results(self, auth_client):
        client, user, website = auth_client
        audit = LLMRankingAuditFactory(
            website=website, created_by=user,
            status=LLMRankingAudit.STATUS_COMPLETED,
            overall_score=72,
        )
        LLMRankingResultFactory(audit=audit, provider="claude", is_mentioned=True)
        LLMRankingResultFactory(audit=audit, provider="gpt4", is_mentioned=False)

        response = client.get(f"/api/v1/llm-ranking/{website.id}/audits/{audit.id}/")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["overall_score"] == 72
        assert len(data["results"]) == 2

    def test_get_audit_not_found(self, auth_client):
        client, user, website = auth_client
        import uuid
        response = client.get(f"/api/v1/llm-ranking/{website.id}/audits/{uuid.uuid4()}/")
        assert response.status_code == 404

    def test_delete_audit(self, auth_client):
        client, user, website = auth_client
        audit = LLMRankingAuditFactory(website=website, created_by=user)
        response = client.delete(f"/api/v1/llm-ranking/{website.id}/audits/{audit.id}/")
        assert response.status_code == 204
        assert not LLMRankingAudit.objects.filter(id=audit.id).exists()

    def test_cannot_access_other_users_audit(self, auth_client):
        client, user, website = auth_client
        other_website = WebsiteFactory()
        audit = LLMRankingAuditFactory(website=other_website)
        response = client.get(f"/api/v1/llm-ranking/{website.id}/audits/{audit.id}/")
        assert response.status_code == 404


@pytest.mark.django_db
class TestLLMRankingProviderBreakdownView:
    def test_breakdown_groups_by_provider(self, auth_client):
        client, user, website = auth_client
        audit = LLMRankingAuditFactory(
            website=website, created_by=user,
            status=LLMRankingAudit.STATUS_COMPLETED,
        )
        LLMRankingResultFactory(audit=audit, provider="claude", is_mentioned=True, mention_rank=1)
        LLMRankingResultFactory(audit=audit, provider="claude", is_mentioned=False)
        LLMRankingResultFactory(audit=audit, provider="gpt4", is_mentioned=True, mention_rank=2)

        response = client.get(
            f"/api/v1/llm-ranking/{website.id}/audits/{audit.id}/breakdown/"
        )
        assert response.status_code == 200
        breakdown = response.json()["data"]
        providers = {b["provider"]: b for b in breakdown}

        assert "claude" in providers
        assert providers["claude"]["total_prompts"] == 2
        assert providers["claude"]["mentioned"] == 1
        assert providers["claude"]["mention_rate"] == 50.0

        assert "gpt4" in providers
        assert providers["gpt4"]["mentioned"] == 1
        assert providers["gpt4"]["avg_rank"] == 2.0


@pytest.mark.django_db
class TestLLMRankingRecommendationsView:
    def test_recommendations_returned_for_completed_audit(self, auth_client):
        client, user, website = auth_client
        audit = LLMRankingAuditFactory(
            website=website, created_by=user,
            status=LLMRankingAudit.STATUS_COMPLETED,
            overall_score=40,
            mention_rate=30.0,
        )
        response = client.get(
            f"/api/v1/llm-ranking/{website.id}/audits/{audit.id}/recommendations/"
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert "recommendations" in data
        assert isinstance(data["recommendations"], list)
        assert len(data["recommendations"]) >= 1

    def test_recommendations_blocked_for_pending_audit(self, auth_client):
        client, user, website = auth_client
        audit = LLMRankingAuditFactory(
            website=website, created_by=user,
            status=LLMRankingAudit.STATUS_PENDING,
        )
        response = client.get(
            f"/api/v1/llm-ranking/{website.id}/audits/{audit.id}/recommendations/"
        )
        assert response.status_code == 400


@pytest.mark.django_db
class TestLLMRankingHistoryView:
    def test_history_returns_completed_audits_only(self, auth_client):
        client, user, website = auth_client
        LLMRankingAuditFactory(
            website=website, created_by=user,
            status=LLMRankingAudit.STATUS_COMPLETED, overall_score=60,
        )
        LLMRankingAuditFactory(
            website=website, created_by=user,
            status=LLMRankingAudit.STATUS_PENDING, overall_score=0,
        )
        response = client.get(f"/api/v1/llm-ranking/{website.id}/history/")
        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) == 1
        assert data[0]["overall_score"] == 60
