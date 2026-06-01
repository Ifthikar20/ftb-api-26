"""Tests for the prompt crawler service."""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from apps.llm_ranking.models import LLMRankingAudit, LLMRankingResult
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


@pytest.mark.django_db
def test_crawl_prompt_runs_extraction_and_captures_competitors(settings):
    """The crawl must run the real extractor so competitor brand names
    in the response are captured, not just a substring check on the
    user's own brand."""
    settings.CITATION_EXTRACTION_ENABLED = False
    website = WebsiteFactory(name="AcmePizza")
    prompt = Prompt.objects.create(text="pizza ordering app in dfw")

    fake_result = SimpleNamespace(
        succeeded=True,
        text="The best options are Domino's, Pizza Hut, and AcmePizza.",
        error="",
    )
    fake_provider = MagicMock()
    fake_provider.query.return_value = fake_result

    extraction = {
        "is_mentioned": True,
        "mention_rank": 3,
        "sentiment": "positive",
        "mention_context": "and AcmePizza",
        "is_linked": False,
        "competitors_mentioned": [
            {"name": "Domino's", "position": 1, "linked": False},
            {"name": "Pizza Hut", "position": 2, "linked": False},
        ],
        "primary_recommendation": "Domino's",
        "citations": [],
        "confidence_score": 92.0,
        "extraction_model": "haiku",
        "extraction_version": "1",
    }

    with patch(
        "apps.prompt_library.services.prompt_crawler._llm_fanout",
        return_value=[],
    ), patch(
        "apps.prompt_library.services.prompt_crawler.list_model_variants",
        return_value=[SimpleNamespace(configured=True, provider="claude")],
    ), patch(
        "apps.prompt_library.services.prompt_crawler.PROVIDERS",
        {"claude": lambda: fake_provider},
    ), patch(
        "apps.llm_ranking.services.extraction_service.HaikuExtractionService.extract",
        return_value=extraction,
    ):
        crawl_prompt(website, prompt)

    row = LLMRankingResult.objects.get(audit__website=website, provider="claude")
    assert row.is_mentioned is True
    assert row.mention_rank == 3
    assert row.sentiment == "positive"
    names = {c["name"] for c in row.competitors_mentioned}
    assert names == {"Domino's", "Pizza Hut"}


@pytest.mark.django_db
def test_crawl_prompt_records_failed_provider_row(settings):
    """A provider that returns succeeded=False gets a row flagged with
    the error, and does not count as a logged response."""
    settings.CITATION_EXTRACTION_ENABLED = False
    website = WebsiteFactory()
    prompt = Prompt.objects.create(text="pizza ordering app in dfw")

    fake_result = SimpleNamespace(
        succeeded=False, text="",
        error="service_unavailable: gemini provider not enabled",
    )
    fake_provider = MagicMock()
    fake_provider.query.return_value = fake_result

    with patch(
        "apps.prompt_library.services.prompt_crawler._llm_fanout",
        return_value=[],
    ), patch(
        "apps.prompt_library.services.prompt_crawler.list_model_variants",
        return_value=[SimpleNamespace(configured=True, provider="gemini")],
    ), patch(
        "apps.prompt_library.services.prompt_crawler.PROVIDERS",
        {"gemini": lambda: fake_provider},
    ):
        outcome = crawl_prompt(website, prompt)

    row = LLMRankingResult.objects.get(audit__website=website, provider="gemini")
    assert row.query_succeeded is False
    assert row.error_message.startswith("service_unavailable")
    assert outcome.responses == 0
