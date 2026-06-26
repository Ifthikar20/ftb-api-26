"""Tests for the agent runner."""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from apps.accounts.tests.factories import UserFactory
from apps.agents.models import AgentAction, HiredAgent
from apps.agents.services.runner import run_agent
from apps.websites.tests.factories import WebsiteFactory


def _fake_provider(payload_text: str):
    p = SimpleNamespace(name="claude")
    p.query = lambda *a, **k: SimpleNamespace(
        text=payload_text, succeeded=True, input_tokens=10, output_tokens=20
    )
    return p


@pytest.mark.django_db
def test_run_agent_creates_insight_and_filters_actions():
    user = UserFactory()
    website = WebsiteFactory(user=user)
    agent = HiredAgent.objects.create(
        user=user, website=website, created_by=user, agent_key="visibility_analyst",
    )
    payload = json.dumps({
        "title": "Visibility up 5 points",
        "summary_markdown": "Your AI mention rate rose this week.",
        "key_points": ["Claude mentions you more often"],
        "proposed_actions": [
            {"action_type": "notify", "title": "Check Perplexity", "params": {"message": "look"}},
            {"action_type": "publish_blog", "title": "not allowed", "params": {}},
        ],
    })
    with patch("apps.llm_ranking.providers.get_provider", return_value=_fake_provider(payload)), \
         patch("apps.llm_ranking.providers.get_synthesis_provider", return_value=None), \
         patch("apps.rag.services.retriever.retrieve_context_block", return_value=""):
        insight = run_agent(agent, deliver=False)

    assert insight.title == "Visibility up 5 points"
    actions = AgentAction.objects.filter(hired_agent=agent)
    # publish_blog is not in the agent's allowed_action_types -> dropped.
    assert actions.count() == 1
    assert actions.first().action_type == "notify"
    assert actions.first().status == AgentAction.STATUS_PROPOSED

    agent.refresh_from_db()
    assert agent.last_run_at is not None
    assert agent.consecutive_failures == 0


@pytest.mark.django_db
def test_run_agent_falls_back_without_provider():
    user = UserFactory()
    website = WebsiteFactory(user=user)
    agent = HiredAgent.objects.create(
        user=user, website=website, created_by=user, agent_key="lead_scout",
    )
    with patch("apps.llm_ranking.providers.get_provider", return_value=None), \
         patch("apps.llm_ranking.providers.get_synthesis_provider", return_value=None), \
         patch("apps.rag.services.retriever.retrieve_context_block", return_value=""):
        insight = run_agent(agent, deliver=False)
    # Deterministic fallback still produces a usable insight.
    assert insight.title
    assert AgentAction.objects.filter(hired_agent=agent).count() == 0
