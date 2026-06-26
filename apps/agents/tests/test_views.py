"""API tests for the agents endpoints."""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.agents.models import HiredAgent
from apps.websites.tests.factories import WebsiteFactory


@pytest.fixture
def auth():
    user = UserFactory()
    website = WebsiteFactory(user=user)
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user, website


@pytest.mark.django_db
def test_catalog_requires_auth():
    assert APIClient().get("/api/v1/agents/catalog/").status_code == 401


@pytest.mark.django_db
def test_catalog_lists_agents(auth):
    client, _user, _website = auth
    resp = client.get("/api/v1/agents/catalog/")
    assert resp.status_code == 200
    body = resp.json()["data"]  # unwrap the global success/data envelope
    keys = {a["key"] for a in body["data"]}
    assert {"visibility_analyst", "citation_hunter", "brand_watchdog"} <= keys
    assert body["capacity"]["max_agents"] == 1  # individual plan


@pytest.mark.django_db
def test_hire_creates_agent(auth):
    client, user, website = auth
    resp = client.post(
        "/api/v1/agents/hire/",
        {"agent_key": "visibility_analyst", "website_id": str(website.id)},
        format="json",
    )
    assert resp.status_code == 201
    assert HiredAgent.objects.filter(
        user=user, website=website, agent_key="visibility_analyst"
    ).exists()


@pytest.mark.django_db
def test_hire_respects_plan_limit(auth):
    client, user, website = auth
    w2 = WebsiteFactory(user=user)
    r1 = client.post(
        "/api/v1/agents/hire/",
        {"agent_key": "visibility_analyst", "website_id": str(website.id)},
        format="json",
    )
    assert r1.status_code == 201
    # Individual plan max_agents == 1 -> second hire blocked.
    r2 = client.post(
        "/api/v1/agents/hire/",
        {"agent_key": "lead_scout", "website_id": str(w2.id)},
        format="json",
    )
    assert r2.status_code == 402


@pytest.mark.django_db
def test_action_decision_other_user_blocked(auth):
    client, _user, _website = auth
    # An action belonging to a different user must 404.
    other = UserFactory()
    ow = WebsiteFactory(user=other)
    oa = HiredAgent.objects.create(
        user=other, website=ow, created_by=other, agent_key="lead_scout",
    )
    from apps.agents.models import AgentAction
    action = AgentAction.objects.create(
        hired_agent=oa, action_type="notify", title="x",
    )
    resp = client.post(f"/api/v1/agents/actions/{action.id}/approve/")
    assert resp.status_code == 404
