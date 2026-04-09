"""Tests for the voice agent onboarding service: templates + setup checklist."""

import pytest

from apps.voice_agent.models import (
    AgentContextDocument,
    CallCampaign,
    PhoneNumber,
)
from apps.voice_agent.services import onboarding
from apps.websites.models import Website


@pytest.fixture
def user(db):
    from apps.accounts.models import User

    return User.objects.create_user(
        email="owner@acme.test", password="x", full_name="Owner"
    )


@pytest.fixture
def website(db, user):
    return Website.objects.create(name="Acme", url="https://acme.test", user=user)


def test_list_templates_all():
    out = onboarding.list_templates()
    slugs = [t.slug for t in out]
    assert "introduction" in slugs
    assert "outbound_sales_script" in slugs
    assert len(out) >= 5


def test_list_templates_inbound_filters_outbound_only():
    out = onboarding.list_templates(onboarding.SEGMENT_INBOUND)
    slugs = [t.slug for t in out]
    assert "outbound_sales_script" not in slugs
    assert "introduction" in slugs  # tagged "both"
    assert "business_hours" in slugs


def test_list_templates_outbound_filters_inbound_only():
    out = onboarding.list_templates(onboarding.SEGMENT_OUTBOUND)
    slugs = [t.slug for t in out]
    assert "outbound_sales_script" in slugs
    assert "introduction" in slugs
    assert "business_hours" not in slugs


def test_list_templates_invalid_segment_raises():
    with pytest.raises(ValueError):
        onboarding.list_templates("nonsense")


def test_render_template_substitutes_business_name():
    out = onboarding.render_template("introduction", business_name="Acme Co")
    assert "Acme Co" in out
    assert "{{business_name}}" not in out


def test_apply_template_creates_doc(website):
    doc = onboarding.apply_template(website=website, slug="introduction")
    assert isinstance(doc, AgentContextDocument)
    assert doc.title == "Introduction & Persona"
    assert doc.is_active is True
    assert "PAM" in doc.content


def test_apply_template_idempotent(website):
    onboarding.apply_template(website=website, slug="introduction")
    onboarding.apply_template(website=website, slug="introduction")
    assert (
        AgentContextDocument.objects.filter(
            website=website, title="Introduction & Persona"
        ).count()
        == 1
    )


def test_setup_status_inbound_progress(website):
    status = onboarding.setup_status(website)
    assert status["inbound"]["complete"] is False
    assert status["inbound"]["progress"] == 0
    # All steps start undone
    assert all(step["done"] is False for step in status["inbound"]["steps"])


def test_setup_status_marks_intro_done_after_apply(website):
    onboarding.apply_template(website=website, slug="introduction")
    status = onboarding.setup_status(website)
    intro_step = next(
        s for s in status["inbound"]["steps"] if s["key"] == "introduction_doc"
    )
    assert intro_step["done"] is True
    assert status["inbound"]["progress"] > 0


def test_setup_status_outbound_marks_provisioned_number(website):
    PhoneNumber.objects.create(
        website=website,
        number="+15550000000",
        provider=PhoneNumber.PROVIDER_TELNYX,
        livekit_outbound_trunk_id="trunk_xyz",
    )
    status = onboarding.setup_status(website)
    from_step = next(
        s for s in status["outbound"]["steps"] if s["key"] == "from_number"
    )
    assert from_step["done"] is True


def test_setup_status_outbound_marks_first_campaign(website):
    pn = PhoneNumber.objects.create(
        website=website,
        number="+15550000000",
        livekit_outbound_trunk_id="trunk_xyz",
    )
    CallCampaign.objects.create(
        website=website,
        name="Q2 push",
        welcome_message="hi",
        from_number=pn,
    )
    status = onboarding.setup_status(website)
    camp_step = next(
        s for s in status["outbound"]["steps"] if s["key"] == "first_campaign"
    )
    assert camp_step["done"] is True
