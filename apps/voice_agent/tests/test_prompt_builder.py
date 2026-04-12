"""Tests for the voice agent system prompt builder."""

import pytest

from apps.voice_agent.models import AgentConfig, AgentContextDocument
from apps.voice_agent.services import prompt_builder
from apps.voice_agent.services.prompt_builder import (
    MAX_PROMPT_CHARS,
    build_retell_system_prompt,
)
from apps.websites.models import Website


@pytest.fixture
def user(db):
    from apps.accounts.models import User
    return User.objects.create_user(email="pb@test.com", password="x", full_name="PB")


@pytest.fixture
def website(db, user):
    return Website.objects.create(name="Acme", url="https://acme.test", user=user)


@pytest.fixture
def config(db, website):
    return AgentConfig.objects.create(
        website=website,
        system_prompt="You are Acme's assistant.",
        business_context="",
        business_hours={},
    )


def test_empty_kb_returns_base_prompt(config):
    out = build_retell_system_prompt(config)
    assert out == "You are Acme's assistant."


def test_business_context_included(config):
    config.business_context = "Acme sells widgets since 1999."
    config.save()
    out = build_retell_system_prompt(config)
    assert "You are Acme's assistant." in out
    assert "Acme sells widgets since 1999." in out


def test_inactive_docs_excluded(config, website):
    AgentContextDocument.objects.create(
        website=website, title="Hours", content="9-5 M-F", is_active=True
    )
    AgentContextDocument.objects.create(
        website=website, title="Secret", content="hush", is_active=False
    )
    out = build_retell_system_prompt(config)
    assert "9-5 M-F" in out
    assert "Hours" in out
    assert "hush" not in out
    assert "Secret" not in out


def test_docs_ordered_by_sort_order(config, website):
    AgentContextDocument.objects.create(
        website=website, title="Second", content="bbb", sort_order=10
    )
    AgentContextDocument.objects.create(
        website=website, title="First", content="aaa", sort_order=1
    )
    out = build_retell_system_prompt(config)
    assert out.index("aaa") < out.index("bbb")
    assert out.index("First") < out.index("Second")


def test_blank_content_doc_skipped(config, website):
    AgentContextDocument.objects.create(
        website=website, title="Empty", content="   ", is_active=True
    )
    AgentContextDocument.objects.create(
        website=website, title="Real", content="real content", is_active=True
    )
    out = build_retell_system_prompt(config)
    assert "Empty" not in out
    assert "real content" in out


def test_truncation_at_max_chars(config, website, monkeypatch):
    monkeypatch.setattr(prompt_builder, "MAX_PROMPT_CHARS", 200)
    AgentContextDocument.objects.create(
        website=website, title="Big", content="x" * 5000, is_active=True
    )
    out = build_retell_system_prompt(config)
    assert len(out) == 200


def test_kb_section_header_present(config, website):
    AgentContextDocument.objects.create(
        website=website, title="FAQ", content="Q1\nA1", is_active=True
    )
    out = build_retell_system_prompt(config)
    assert "# Knowledge Base" in out
    assert "## FAQ" in out


def test_default_max_constant_is_reasonable():
    assert MAX_PROMPT_CHARS >= 4000
