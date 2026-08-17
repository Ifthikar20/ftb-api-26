"""Regression tests for the hired-agent cross-tenant IDOR (P0.2).

A PATCH to /api/v1/agents/hired/<id>/ must not let a user repoint their
agent at another tenant's website, nor bind another tenant's Slack
IntegrationConnection.
"""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.agents.models import HiredAgent
from apps.websites.tests.factories import WebsiteFactory


@pytest.fixture
def hired():
    user = UserFactory()
    website = WebsiteFactory(user=user)
    agent = HiredAgent.objects.create(
        user=user, website=website, created_by=user, agent_key="visibility_analyst",
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user, website, agent


@pytest.mark.django_db
def test_patch_cannot_repoint_agent_at_another_tenants_website(hired):
    client, _user, own_website, agent = hired
    victim = UserFactory()
    victim_website = WebsiteFactory(user=victim)

    client.patch(
        f"/api/v1/agents/hired/{agent.id}/",
        {"website": str(victim_website.id)},
        format="json",
    )

    # website is read-only: the request may 200 (field ignored) but the
    # binding must not change. Assert on the persisted state either way.
    agent.refresh_from_db()
    assert agent.website_id == own_website.id
    assert agent.website_id != victim_website.id


@pytest.mark.django_db
def test_patch_cannot_bind_another_tenants_slack_connection(hired):
    client, _user, _own_website, agent = hired
    victim = UserFactory()
    from apps.notifications.models import IntegrationConnection

    victim_conn = IntegrationConnection.objects.create(
        user=victim, platform="slack", is_active=True,
    )

    resp = client.patch(
        f"/api/v1/agents/hired/{agent.id}/",
        {"slack_connection": str(victim_conn.id)},
        format="json",
    )

    assert resp.status_code == 400
    agent.refresh_from_db()
    assert agent.slack_connection_id is None


@pytest.mark.django_db
def test_patch_allows_editing_own_agent_fields(hired):
    client, _user, _own_website, agent = hired
    resp = client.patch(
        f"/api/v1/agents/hired/{agent.id}/",
        {"is_active": False, "frequency": HiredAgent.FREQUENCY_WEEKLY},
        format="json",
    )
    assert resp.status_code == 200
    agent.refresh_from_db()
    assert agent.is_active is False
    assert agent.frequency == HiredAgent.FREQUENCY_WEEKLY


@pytest.mark.django_db
def test_patch_allows_binding_own_slack_connection(hired):
    client, user, _own_website, agent = hired
    from apps.notifications.models import IntegrationConnection

    own_conn = IntegrationConnection.objects.create(
        user=user, platform="slack", is_active=True,
    )
    resp = client.patch(
        f"/api/v1/agents/hired/{agent.id}/",
        {"slack_connection": str(own_conn.id)},
        format="json",
    )
    assert resp.status_code == 200
    agent.refresh_from_db()
    assert agent.slack_connection_id == own_conn.id
