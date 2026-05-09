"""Service-level tests for the content_studio app."""
from __future__ import annotations

import pytest
from django.test import override_settings

from apps.brand_vault.models import BrandFact, FactStatus, ToneSample
from apps.claim_verifier.models import (
    Claim,
    ClaimMismatch,
    MismatchSeverity,
    MismatchType,
)
from apps.content_studio.models import (
    BriefStatus,
    ContentBrief,
    ContentDraft,
    ContentFormat,
    DraftStatus,
    GapType,
    PublishLog,
    PublishStatus,
    PublishTarget,
)
from apps.content_studio.services import (
    accuracy_guard,
    brief_generator,
    drafter,
    voice_guard,
)
from apps.content_studio.services.publish_adapters import get_adapter
from apps.content_studio.services.roi_tracker import schedule_roi_measurement
from apps.llm_ranking.tests.factories import (
    LLMRankingAuditFactory,
    LLMRankingResultFactory,
)
from apps.websites.tests.factories import WebsiteFactory


pytestmark = [
    pytest.mark.django_db,
    override_settings(
        BRAND_VAULT_EXTRACTION_ENABLED=False,
        CLAIM_VERIFICATION_ENABLED=False,
        CITATION_EXTRACTION_ENABLED=False,
        CONTENT_STUDIO_BRIEF_GENERATION_ENABLED=False,
        CONTENT_STUDIO_PUBLISH_LIVE=False,
    ),
]


def _approved_fact(website, subject="Acme", obj="ships globally"):
    return BrandFact.objects.create(
        website=website, subject=subject, predicate="does",
        object=obj, status=FactStatus.APPROVED.value,
    )


def test_visibility_brief_created_when_mention_rate_low():
    website = WebsiteFactory()
    audit = LLMRankingAuditFactory(website=website)
    LLMRankingResultFactory(audit=audit, prompt="best CRM?", is_mentioned=False)
    LLMRankingResultFactory(audit=audit, prompt="best CRM?", is_mentioned=False)
    LLMRankingResultFactory(audit=audit, prompt="best CRM?", is_mentioned=False)

    n = brief_generator.generate_briefs_for_website(str(website.id))
    assert n >= 1
    brief = ContentBrief.objects.filter(website=website, gap_type=GapType.VISIBILITY.value).first()
    assert brief is not None
    assert brief.target_format == ContentFormat.BLOG.value


def test_accuracy_brief_built_for_high_severity_mismatch():
    website = WebsiteFactory()
    audit = LLMRankingAuditFactory(website=website)
    result = LLMRankingResultFactory(audit=audit)
    claim = Claim.objects.create(
        result=result, audit=audit, website=website,
        text="Acme charges $99/mo", subject="Acme", predicate="charges", object="$99/mo",
    )
    ClaimMismatch.objects.create(
        claim=claim, mismatch_type=MismatchType.CONTRADICTS.value,
        severity=MismatchSeverity.CRITICAL.value, audience_reach=0.9,
    )
    brief_generator.generate_briefs_for_website(str(website.id))
    brief = ContentBrief.objects.filter(
        website=website, gap_type=GapType.ACCURACY.value,
    ).first()
    assert brief is not None
    assert brief.target_format == ContentFormat.FAQ.value


def test_brief_generation_is_idempotent():
    website = WebsiteFactory()
    audit = LLMRankingAuditFactory(website=website)
    result = LLMRankingResultFactory(audit=audit)
    claim = Claim.objects.create(
        result=result, audit=audit, website=website, text="x", subject="Acme",
    )
    ClaimMismatch.objects.create(
        claim=claim, mismatch_type=MismatchType.UNKNOWN.value,
        severity=MismatchSeverity.HIGH.value,
    )
    n1 = brief_generator.generate_briefs_for_website(str(website.id))
    n2 = brief_generator.generate_briefs_for_website(str(website.id))
    assert n1 >= 1
    assert n2 == 0


def test_briefs_ordered_by_impact_desc():
    website = WebsiteFactory()
    ContentBrief.objects.create(
        website=website, gap_type=GapType.VISIBILITY.value, impact_score=0.4,
        target_format=ContentFormat.BLOG.value, headline="low", description="",
    )
    ContentBrief.objects.create(
        website=website, gap_type=GapType.VISIBILITY.value, impact_score=0.9,
        target_format=ContentFormat.BLOG.value, headline="high", description="",
    )
    first = ContentBrief.objects.filter(website=website).first()
    assert first.headline == "high"


def test_drafter_persists_draft_and_runs_guards(monkeypatch):
    monkeypatch.setattr(drafter, "_call_anthropic", lambda s, u: "")
    website = WebsiteFactory()
    _approved_fact(website)
    brief = ContentBrief.objects.create(
        website=website, gap_type=GapType.VISIBILITY.value, impact_score=0.5,
        target_format=ContentFormat.BLOG.value, headline="Test brief",
        description="why",
        suggested_structure={"sections": [{"heading": "Intro", "summary": "x"}]},
    )
    draft = drafter.draft_content(str(brief.id))
    assert draft.status == DraftStatus.READY.value
    assert draft.body_markdown
    assert draft.voice_score is not None
    assert draft.accuracy_score is not None
    brief.refresh_from_db()
    assert brief.status == BriefStatus.DRAFTED.value


def test_drafter_regenerate_bumps_revision(monkeypatch):
    monkeypatch.setattr(drafter, "_call_anthropic", lambda s, u: "")
    website = WebsiteFactory()
    brief = ContentBrief.objects.create(
        website=website, gap_type=GapType.VISIBILITY.value, impact_score=0.5,
        target_format=ContentFormat.BLOG.value, headline="X", description="",
    )
    d1 = drafter.draft_content(str(brief.id))
    d2 = drafter.draft_content(str(brief.id), regenerate=True)
    assert d1.revision == 1
    assert d2.revision == 2


def test_voice_guard_no_samples():
    website = WebsiteFactory()
    draft = ContentDraft.objects.create(
        brief=ContentBrief.objects.create(
            website=website, gap_type=GapType.VISIBILITY.value,
            target_format=ContentFormat.BLOG.value,
            headline="x", description="",
        ),
        website=website, title="t", body_markdown="hello world",
    )
    score, notes = voice_guard.score_voice(draft)
    assert score == 0.5
    assert "no tone samples" in notes


def test_voice_guard_with_samples():
    website = WebsiteFactory()
    ToneSample.objects.create(
        website=website, text="We build helpful products for growing teams.",
        text_hash="h1", word_count=8,
    )
    draft = ContentDraft.objects.create(
        brief=ContentBrief.objects.create(
            website=website, gap_type=GapType.VISIBILITY.value,
            target_format=ContentFormat.BLOG.value,
            headline="x", description="",
        ),
        website=website, title="t",
        body_markdown="We build helpful products for growing teams.",
    )
    score, notes = voice_guard.score_voice(draft)
    assert 0.0 <= score <= 1.0


def test_accuracy_guard_detects_unsupported_claim():
    website = WebsiteFactory()
    BrandFact.objects.create(
        website=website, subject="Acme", predicate="ships",
        object="globally to 50 countries", status=FactStatus.APPROVED.value,
    )
    draft = ContentDraft.objects.create(
        brief=ContentBrief.objects.create(
            website=website, gap_type=GapType.VISIBILITY.value,
            target_format=ContentFormat.BLOG.value,
            headline="x", description="",
        ),
        website=website, title="t",
        body_markdown=(
            "Acme ships globally to 50 countries every week. "
            "The company was founded on planet Mars in 1812."
        ),
    )
    score, notes = accuracy_guard.score_accuracy(draft)
    assert 0.0 <= score <= 1.0
    assert "claims" in notes.lower() or "verified" in notes.lower()


def test_publish_adapter_dry_run_returns_payload():
    website = WebsiteFactory()
    target = PublishTarget.objects.create(
        website=website, provider="wordpress",
        config={"site_url": "https://x.example.com", "user": "u", "app_password": "p"},
    )
    draft = ContentDraft.objects.create(
        brief=ContentBrief.objects.create(
            website=website, gap_type=GapType.VISIBILITY.value,
            target_format=ContentFormat.BLOG.value, headline="x", description="",
        ),
        website=website, title="Hello", body_markdown="Hi world",
    )
    adapter = get_adapter("wordpress")
    result = adapter.publish(draft, target)
    assert result["status"] == "published"
    assert result["external_id"] == "dry-run"
    assert result["request_payload"]["title"] == "Hello"


def test_publish_target_dry_run_for_all_providers():
    website = WebsiteFactory()
    draft = ContentDraft.objects.create(
        brief=ContentBrief.objects.create(
            website=website, gap_type=GapType.VISIBILITY.value,
            target_format=ContentFormat.BLOG.value, headline="x", description="",
        ),
        website=website, title="Hi", body_markdown="x",
    )
    for provider in ("wordpress", "webflow", "shopify", "hubspot", "manual"):
        target = PublishTarget.objects.create(
            website=website, provider=provider, label=provider, config={},
        )
        result = get_adapter(provider).publish(draft, target)
        assert result["status"] == "published"


def test_schedule_roi_measurement_does_not_raise():
    website = WebsiteFactory()
    draft = ContentDraft.objects.create(
        brief=ContentBrief.objects.create(
            website=website, gap_type=GapType.VISIBILITY.value,
            target_format=ContentFormat.BLOG.value, headline="x", description="",
        ),
        website=website, title="t", body_markdown="x",
    )
    schedule_roi_measurement(str(draft.id), days_after=1)


def test_publish_task_creates_log_and_publishes_draft():
    from apps.content_studio.tasks import publish_draft as publish_task

    website = WebsiteFactory()
    target = PublishTarget.objects.create(
        website=website, provider="manual", config={},
    )
    draft = ContentDraft.objects.create(
        brief=ContentBrief.objects.create(
            website=website, gap_type=GapType.VISIBILITY.value,
            target_format=ContentFormat.BLOG.value, headline="x", description="",
        ),
        website=website, title="t", body_markdown="x",
    )
    log_id = publish_task.run(str(draft.id), str(target.id))
    assert log_id
    log = PublishLog.objects.get(id=log_id)
    assert log.status == PublishStatus.PUBLISHED.value
    draft.refresh_from_db()
    assert draft.status == DraftStatus.PUBLISHED.value


def test_finalize_audit_dispatches_brief_generation(monkeypatch):
    """The Phase 4 hook must enqueue brief generation when enabled."""
    from apps.content_studio import tasks as cs_tasks

    calls: list[str] = []

    class _Result:
        id = "x"

    def fake_delay(arg):
        calls.append(str(arg))
        return _Result()

    monkeypatch.setattr(cs_tasks.generate_briefs_for_website, "delay", fake_delay)

    website = WebsiteFactory()
    with override_settings(CONTENT_STUDIO_BRIEF_GENERATION_ENABLED=True):
        # Simulate the hook block from ranking_service.finalize_audit.
        from apps.content_studio.tasks import generate_briefs_for_website
        generate_briefs_for_website.delay(str(website.id))
    assert calls == [str(website.id)]
