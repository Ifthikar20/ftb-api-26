"""API tests for the prompt_library endpoints."""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.llm_ranking.tests.factories import LLMRankingAuditFactory
from apps.prompt_library.models import BrandPrompt
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


@pytest.mark.django_db
def test_add_and_list_brand_prompt(auth):
    client, _, website = auth
    industry = IndustryFactory(slug="food-bev")
    p = PromptFactory(industry=industry, text="Cooking bread pudding at home")
    add = client.post(
        f"/api/v1/prompt-library/websites/{website.id}/brand-prompts/",
        {"prompt_id": str(p.id)},
        format="json",
    )
    assert add.status_code == 201
    body = add.json()
    bp_id = body.get("id") or body.get("data", {}).get("id")
    assert bp_id

    listing = client.get(f"/api/v1/prompt-library/websites/{website.id}/brand-prompts/")
    assert listing.status_code == 200
    rows = listing.json()
    rows = rows.get("data", rows) if isinstance(rows, dict) else rows
    assert any(r["prompt"]["id"] == str(p.id) for r in rows)


@pytest.mark.django_db
def test_add_brand_prompt_idempotent(auth):
    client, _, website = auth
    p = PromptFactory()
    first = client.post(
        f"/api/v1/prompt-library/websites/{website.id}/brand-prompts/",
        {"prompt_id": str(p.id)},
        format="json",
    )
    second = client.post(
        f"/api/v1/prompt-library/websites/{website.id}/brand-prompts/",
        {"prompt_id": str(p.id)},
        format="json",
    )
    assert first.status_code == 201
    assert second.status_code == 200
    assert BrandPrompt.objects.filter(website=website, prompt=p).count() == 1


@pytest.mark.django_db
def test_remove_brand_prompt(auth):
    client, _, website = auth
    p = PromptFactory()
    add = client.post(
        f"/api/v1/prompt-library/websites/{website.id}/brand-prompts/",
        {"prompt_id": str(p.id)},
        format="json",
    )
    bp_id = add.json().get("id") or add.json().get("data", {}).get("id")
    delete = client.delete(f"/api/v1/prompt-library/brand-prompts/{bp_id}/")
    assert delete.status_code == 204
    assert not BrandPrompt.objects.filter(id=bp_id).exists()


@pytest.mark.django_db
def test_brand_prompt_other_user_blocked():
    industry = IndustryFactory()
    p = PromptFactory(industry=industry)
    other_user = UserFactory()
    other_website = WebsiteFactory(user=other_user)

    intruder = UserFactory()
    client = APIClient()
    client.force_authenticate(user=intruder)
    resp = client.post(
        f"/api/v1/prompt-library/websites/{other_website.id}/brand-prompts/",
        {"prompt_id": str(p.id)},
        format="json",
    )
    assert resp.status_code in (403, 404)


@pytest.mark.django_db
def test_create_prompt_with_new_topic(auth):
    client, _, website = auth
    # Need at least one active industry so the no-topic default path exists,
    # but here we pass an explicit new topic name.
    resp = client.post(
        f"/api/v1/prompt-library/websites/{website.id}/prompts/",
        {"text": "What are the best budgeting apps in 2026?", "topic": "ALi"},
        format="json",
    )
    assert resp.status_code == 201, resp.content
    body = resp.json()
    assert body.get("brand_prompt_id")
    # A BrandPrompt linked to a Prompt filed under the new "ALi" topic.
    bp = BrandPrompt.objects.select_related("prompt__industry").get(
        id=body["brand_prompt_id"],
    )
    assert bp.website_id == website.id
    assert bp.prompt.industry.name == "ALi"
    assert bp.prompt.text == "What are the best budgeting apps in 2026?"


@pytest.mark.django_db
def test_create_prompt_reuses_existing_topic(auth):
    client, _, website = auth
    industry = IndustryFactory(name="ALi", slug="ali")
    resp = client.post(
        f"/api/v1/prompt-library/websites/{website.id}/prompts/",
        {"text": "How do I automate cash flow?", "topic": "ALi"},
        format="json",
    )
    assert resp.status_code == 201, resp.content
    bp = BrandPrompt.objects.select_related("prompt__industry").get(
        id=resp.json()["brand_prompt_id"],
    )
    assert bp.prompt.industry_id == industry.id


@pytest.mark.django_db
def test_create_prompt_requires_text(auth):
    client, _, website = auth
    resp = client.post(
        f"/api/v1/prompt-library/websites/{website.id}/prompts/",
        {"topic": "ALi"},
        format="json",
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_prompt_detail_returns_recent_chats(auth):
    from apps.citations.services.extraction_service import extract_for_result
    from apps.llm_ranking.models import LLMRankingResult
    from apps.llm_ranking.tests.factories import LLMRankingResultFactory

    client, user, website = auth
    industry = IndustryFactory(name="ALi", slug="ali")
    p = PromptFactory(industry=industry, text="best budgeting apps in 2026")
    BrandPrompt.objects.create(website=website, prompt=p)
    audit = LLMRankingAuditFactory(website=website, created_by=user)
    r = LLMRankingResultFactory(
        audit=audit, provider=LLMRankingResult.PROVIDER_PERPLEXITY, prompt_index=0,
        prompt="best budgeting apps in 2026", response_text="Here are some apps...",
        is_mentioned=True, mention_rank=2,
        citations=[{"url": "https://reddit.com/r/x"}],
    )
    extract_for_result(str(r.id))

    resp = client.get(
        f"/api/v1/prompt-library/websites/{website.id}/prompts/{p.id}/detail/"
    )
    assert resp.status_code == 200, resp.content
    body = resp.json()
    assert body["prompt"]["topic"] == "ALi"
    chats = body["recent_chats"]
    assert len(chats) == 1
    chat = chats[0]
    assert chat["result_id"] == str(r.id)
    assert chat["brand_mentioned"] is True
    assert chat["position"] == 2
    assert chat["models"] == ["perplexity"]
    assert "reddit.com" in chat["sources"]


@pytest.mark.django_db
def test_create_prompts_multiline_with_tags_and_location(auth, monkeypatch):
    import apps.llm_ranking.tasks as lr_tasks
    monkeypatch.setattr(lr_tasks.run_llm_ranking_audit, "delay", lambda **k: None)

    client, _, website = auth
    resp = client.post(
        f"/api/v1/prompt-library/websites/{website.id}/prompts/",
        {
            "text": "best budgeting apps\nalternatives to rocket money\n",
            "topic": "ALi",
            "location": "US",
            "tags": ["branded", "transactional"],
        },
        format="json",
    )
    assert resp.status_code == 201, resp.content
    body = resp.json()
    assert body["created_count"] == 2
    assert len(body["brand_prompt_ids"]) == 2

    bps = BrandPrompt.objects.filter(website=website).select_related("prompt__industry")
    assert bps.count() == 2
    for bp in bps:
        assert bp.tags == ["branded", "transactional"]
        assert bp.location == "US"
        assert bp.prompt.industry.name == "ALi"


@pytest.mark.django_db
def test_create_prompt_scan_failure_does_not_break_create(auth, monkeypatch):
    import apps.llm_ranking.tasks as lr_tasks

    def boom(**k):
        raise RuntimeError("queue down")
    monkeypatch.setattr(lr_tasks.run_llm_ranking_audit, "delay", boom)

    client, _, website = auth
    resp = client.post(
        f"/api/v1/prompt-library/websites/{website.id}/prompts/",
        {"text": "a resilient prompt", "topic": "ALi"},
        format="json",
    )
    assert resp.status_code == 201, resp.content
    assert resp.json()["scan_audit_id"] is None
    assert BrandPrompt.objects.filter(website=website).count() == 1
