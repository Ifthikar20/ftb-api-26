"""Tests for the prompt crawler service."""
from unittest.mock import MagicMock, patch

import pytest

from apps.llm_ranking.models import LLMRankingAudit
from apps.prompt_library.models import Prompt, PromptCrawlRun
from apps.prompt_library.services.prompt_crawler import _llm_fanout, crawl_prompt
from apps.websites.tests.factories import WebsiteFactory


@pytest.mark.django_db
def test_crawl_prompt_sets_created_by_to_website_owner():
    """Regression: synchronous crawl path was creating audits without
    created_by, violating the not-null constraint on
    llm_ranking_audit.created_by_id."""
    website = WebsiteFactory()
    prompt = Prompt.objects.create(text="best pizza app in dfw")

    with patch(
        "apps.prompt_library.services.prompt_crawler._llm_fanout",
        return_value=[],
    ), patch(
        "apps.prompt_library.services.prompt_crawler.list_model_variants",
        return_value=[],
    ):
        crawl_prompt(website, prompt)

    audit = LLMRankingAudit.objects.filter(website=website).get()
    assert audit.created_by_id == website.user_id
    assert PromptCrawlRun.objects.filter(website=website, prompt=prompt).exists()


def test_llm_fanout_uses_system_prompt_kwarg(monkeypatch):
    """Regression: provider.query was being called with system= instead
    of system_prompt=, raising a TypeError that fell through to the
    heuristic fallback on every crawl."""
    fake_resp = MagicMock(text='["sub 1", "sub 2"]')
    fake_provider = MagicMock()
    fake_provider.query.return_value = fake_resp

    monkeypatch.setattr(
        "apps.llm_ranking.providers.claude.ClaudeProvider",
        lambda: fake_provider,
    )

    out = _llm_fanout("pizza ordering app in dfw", "AcmePizza")
    assert out == ["sub 1", "sub 2"]
    _, kwargs = fake_provider.query.call_args
    assert "system_prompt" in kwargs
    assert "system" not in kwargs
