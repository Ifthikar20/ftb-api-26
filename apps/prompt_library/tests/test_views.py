"""API tests for the prompt_library endpoints."""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.llm_ranking.tests.factories import LLMRankingAuditFactory
from apps.prompt_library.tests.factories import IndustryFactory, PromptFactory
from apps.websites.tests.factories import WebsiteFactory


@pytest.fixture
def auth():
    user = UserFactory()
    website = WebsiteFactory(user=user)
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user, website


@pytest.mark.django_db
def test_industries_requires_auth():
    anon = APIClient()
    assert anon.get("/api/v1/prompt-library/industries/").status_code == 401


@pytest.mark.django_db
def test_industries_list(auth):
    client, _, _ = auth
    IndustryFactory(name="SaaS / Analytics", slug="saas-analytics")
    IndustryFactory(is_active=False)
    resp = client.get("/api/v1/prompt-library/industries/")
    assert resp.status_code == 200
    names = [row["name"] for row in resp.json()]
    assert "SaaS / Analytics" in names
    assert len(names) == 1  # inactive excluded


@pytest.mark.django_db
def test_prompts_list_filter_by_industry(auth):
    client, _, _ = auth
    industry = IndustryFactory(slug="crm")
    other = IndustryFactory(slug="other")
    PromptFactory(industry=industry, text="how to pick a CRM?")
    PromptFactory(industry=other, text="unrelated")
    resp = client.get("/api/v1/prompt-library/prompts/?industry=crm")
    assert resp.status_code == 200
    body = resp.json()
    rows = body.get("data", body).get("results", body) if isinstance(body, dict) else body
    # Tolerate either a paginated envelope or a flat list.
    if isinstance(rows, dict) and "results" in rows:
        rows = rows["results"]
    assert any("CRM" in r["text"] for r in rows)


@pytest.mark.django_db
def test_preview_sample_returns_prompts(auth):
    client, _, _ = auth
    industry = IndustryFactory()
    for _ in range(5):
        PromptFactory(industry=industry)
    resp = client.post(
        "/api/v1/prompt-library/prompts/preview-sample/",
        {"industry_id": str(industry.id), "n": 3},
        format="json",
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["prompts"]) == 3
    assert body["industry"]["id"] == str(industry.id)


@pytest.mark.django_db
def test_use_library_sample_persists_run(auth):
    client, user, website = auth
    industry = IndustryFactory()
    for _ in range(5):
        PromptFactory(industry=industry)
    audit = LLMRankingAuditFactory(website=website, created_by=user)
    resp = client.post(
        f"/api/v1/prompt-library/audits/{audit.id}/use-library-sample/",
        {"industry_id": str(industry.id), "n": 3, "seed": 7},
        format="json",
    )
    assert resp.status_code == 200, resp.content
    body = resp.json()
    assert body["seed"] == 7
    assert len(body["entries"]) == 3
    audit.refresh_from_db()
    assert audit.prompt_source == "library"


@pytest.mark.django_db
def test_get_audit_sample_returns_null_when_missing(auth):
    client, user, website = auth
    audit = LLMRankingAuditFactory(website=website, created_by=user)
    resp = client.get(f"/api/v1/prompt-library/audits/{audit.id}/sample/")
    assert resp.status_code == 200
    assert resp.json()["sample_run"] is None
