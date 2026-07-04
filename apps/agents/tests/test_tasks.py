"""Tests for the agent dispatcher + action execution tasks."""
from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.agents.models import AgentAction, HiredAgent
from apps.agents.services.actions import execute_action
from apps.agents.tasks import dispatch_agent_runs
from apps.notifications.models import Notification
from apps.websites.tests.factories import WebsiteFactory


@pytest.mark.django_db
def test_dispatch_runs_due_agents_only():
    user = UserFactory()
    w1, w2 = WebsiteFactory(user=user), WebsiteFactory(user=user)
    now = timezone.now()
    due = HiredAgent.objects.create(
        user=user, website=w1, created_by=user, agent_key="visibility_analyst",
        next_run_at=now - timedelta(hours=1),
    )
    not_due = HiredAgent.objects.create(
        user=user, website=w2, created_by=user, agent_key="lead_scout",
        next_run_at=now + timedelta(hours=6),
    )
    with patch("apps.agents.tasks.run_hired_agent.delay") as mock_delay:
        dispatch_agent_runs()

    called = {c.kwargs["hired_agent_id"] for c in mock_delay.call_args_list}
    assert str(due.id) in called
    assert str(not_due.id) not in called

    due.refresh_from_db()
    assert due.next_run_at > now  # advanced


@pytest.mark.django_db
def test_dispatch_skips_user_over_spend_cap():
    user = UserFactory(monthly_ai_cost_cap_usd=10)
    website = WebsiteFactory(user=user)
    agent = HiredAgent.objects.create(
        user=user, website=website, created_by=user, agent_key="visibility_analyst",
        next_run_at=timezone.now() - timedelta(hours=1),
    )
    with patch("core.ai_tracking.month_to_date_cost", return_value=50.0), \
         patch("apps.agents.tasks.run_hired_agent.delay") as mock_delay:
        dispatch_agent_runs()
    mock_delay.assert_not_called()
    agent.refresh_from_db()
    assert agent.next_run_at > timezone.now()  # bumped, not run


@pytest.mark.django_db
def test_action_requires_approval_then_executes():
    user = UserFactory()
    website = WebsiteFactory(user=user)
    agent = HiredAgent.objects.create(
        user=user, website=website, created_by=user, agent_key="lead_scout",
    )
    proposed = AgentAction.objects.create(
        hired_agent=agent, action_type="notify", title="Ping",
        params={"message": "hi"}, status=AgentAction.STATUS_PROPOSED,
    )
    # Unapproved -> skipped, no side effect.
    res = execute_action(proposed)
    assert "skipped" in res
    proposed.refresh_from_db()
    assert proposed.status == AgentAction.STATUS_PROPOSED

    # Approved -> executes and creates a notification.
    proposed.status = AgentAction.STATUS_APPROVED
    proposed.save(update_fields=["status"])
    execute_action(proposed)
    proposed.refresh_from_db()
    assert proposed.status == AgentAction.STATUS_DONE
    assert Notification.objects.filter(user=user, type="agent_action").exists()
