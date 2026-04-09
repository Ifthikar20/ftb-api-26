"""Voice agent onboarding helpers.

Two responsibilities:

1. **Templates** — ship a small library of starter markdown files (introduction,
   services, FAQ, business hours, outbound sales script) so a new B2B user can
   one-click them into their knowledge base instead of staring at a blank editor.

2. **Setup status** — compute a per-website checklist for both the *inbound* and
   *outbound* segments so the UI can render an onboarding progress bar.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from apps.voice_agent.models import (
    AgentConfig,
    AgentContextDocument,
    CallCampaign,
    PhoneNumber,
)

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "onboarding_templates"

# Segment tags so the UI can group templates under "Inbound" / "Outbound" / "Both".
SEGMENT_INBOUND = "inbound"
SEGMENT_OUTBOUND = "outbound"
SEGMENT_BOTH = "both"


@dataclass(frozen=True)
class Template:
    slug: str
    title: str
    description: str
    segment: str  # inbound | outbound | both
    filename: str
    sort_order: int
    recommended: bool = False


# The order here is the order the UI should display them in.
TEMPLATES: tuple[Template, ...] = (
    Template(
        slug="introduction",
        title="Introduction & Persona",
        description=(
            "The default greeting and personality for your AI agent. Start here — "
            "every voice agent should have one."
        ),
        segment=SEGMENT_BOTH,
        filename="introduction.md",
        sort_order=0,
        recommended=True,
    ),
    Template(
        slug="business_hours",
        title="Business Hours & Scheduling",
        description=(
            "Tells the agent when you're open and how to book appointments using "
            "the schedule_appointment tool."
        ),
        segment=SEGMENT_INBOUND,
        filename="business_hours.md",
        sort_order=10,
        recommended=True,
    ),
    Template(
        slug="services_pricing",
        title="Services & Pricing",
        description="What you offer and how much it costs. The agent will quote from this.",
        segment=SEGMENT_BOTH,
        filename="services_pricing.md",
        sort_order=20,
        recommended=True,
    ),
    Template(
        slug="faq",
        title="Frequently Asked Questions",
        description="Common questions the agent should be able to answer without escalating.",
        segment=SEGMENT_BOTH,
        filename="faq.md",
        sort_order=30,
        recommended=True,
    ),
    Template(
        slug="outbound_sales_script",
        title="Outbound Sales Script",
        description=(
            "A proven structure for outbound calls: opening, discovery, pitch, "
            "objection handling, and a clear call-to-action."
        ),
        segment=SEGMENT_OUTBOUND,
        filename="outbound_sales_script.md",
        sort_order=40,
        recommended=True,
    ),
)

_BY_SLUG = {t.slug: t for t in TEMPLATES}


def list_templates(segment: str | None = None) -> list[Template]:
    """Return all templates, optionally filtered to a single segment.

    ``segment="inbound"`` returns templates tagged inbound or both;
    ``segment="outbound"`` returns templates tagged outbound or both.
    """
    if segment is None:
        return list(TEMPLATES)
    if segment not in (SEGMENT_INBOUND, SEGMENT_OUTBOUND, SEGMENT_BOTH):
        raise ValueError(f"unknown segment: {segment}")
    return [
        t
        for t in TEMPLATES
        if t.segment == segment or t.segment == SEGMENT_BOTH
    ]


def get_template(slug: str) -> Template:
    if slug not in _BY_SLUG:
        raise KeyError(slug)
    return _BY_SLUG[slug]


def render_template(slug: str, *, business_name: str = "") -> str:
    """Read the template file from disk and substitute simple placeholders."""
    template = get_template(slug)
    text = (TEMPLATE_DIR / template.filename).read_text(encoding="utf-8")
    return text.replace("{{business_name}}", business_name or "our business")


def apply_template(*, website, slug: str) -> AgentContextDocument:
    """Create an ``AgentContextDocument`` for ``website`` from a template.

    If a doc with the same title already exists for the website, it is updated
    in place rather than duplicated.
    """
    template = get_template(slug)
    business_name = (
        AgentConfig.objects.filter(website=website)
        .values_list("business_name", flat=True)
        .first()
        or ""
    )
    content = render_template(slug, business_name=business_name)

    doc, _ = AgentContextDocument.objects.update_or_create(
        website=website,
        title=template.title,
        defaults={
            "content": content,
            "is_active": True,
            "sort_order": template.sort_order,
        },
    )
    return doc


# ── Setup status ──────────────────────────────────────────────────────────────


@dataclass
class ChecklistItem:
    key: str
    label: str
    description: str
    done: bool
    cta_url: str = ""  # Path the UI should send the user to in order to finish the step


def _has_active_kb(website) -> bool:
    return AgentContextDocument.objects.filter(website=website, is_active=True).exists()


def _has_intro_doc(website) -> bool:
    intro = get_template("introduction")
    return AgentContextDocument.objects.filter(
        website=website, title=intro.title, is_active=True
    ).exists()


def _has_outbound_script(website) -> bool:
    script = get_template("outbound_sales_script")
    return AgentContextDocument.objects.filter(
        website=website, title=script.title, is_active=True
    ).exists()


def inbound_checklist(website) -> list[ChecklistItem]:
    config_row = (
        AgentConfig.objects.filter(website=website)
        .values("id", "is_active", "business_hours")
        .first()
    )
    has_phone = PhoneNumber.objects.filter(
        website=website, is_active=True, forwarded_to_agent=True
    ).exists()
    base = f"/voice-agent/{website.id}"
    return [
        ChecklistItem(
            key="agent_config",
            label="Configure your AI receptionist",
            description=(
                "Pick a business name, greeting, timezone, and appointment length."
            ),
            done=bool(config_row),
            cta_url=f"{base}/config",
        ),
        ChecklistItem(
            key="introduction_doc",
            label="Add the Introduction template",
            description=(
                "Gives the agent its name, tone, and default greeting. We recommend "
                "starting from our template — you can edit it after."
            ),
            done=_has_intro_doc(website),
            cta_url=f"{base}/knowledge-base?template=introduction",
        ),
        ChecklistItem(
            key="knowledge_base",
            label="Add at least one knowledge-base document",
            description=(
                "Services, pricing, FAQs — anything callers might ask about. The "
                "agent will read these on every call."
            ),
            done=_has_active_kb(website),
            cta_url=f"{base}/knowledge-base",
        ),
        ChecklistItem(
            key="business_hours",
            label="Set business hours",
            description="So the agent knows when to book appointments and when to take messages.",
            done=bool(config_row and config_row.get("business_hours")),
            cta_url=f"{base}/config#hours",
        ),
        ChecklistItem(
            key="phone_number",
            label="Add a phone number",
            description=(
                "Add the business number callers will dial. You can forward your "
                "existing number to it."
            ),
            done=has_phone,
            cta_url=f"{base}/phone-numbers",
        ),
        ChecklistItem(
            key="agent_active",
            label="Activate the agent",
            description="Flip the switch to start answering live calls.",
            done=bool(config_row and config_row.get("is_active")),
            cta_url=f"{base}/config",
        ),
    ]


def outbound_checklist(website) -> list[ChecklistItem]:
    has_outbound_number = PhoneNumber.objects.filter(
        website=website, is_active=True
    ).exclude(livekit_outbound_trunk_id="").exists()
    has_campaign = CallCampaign.objects.filter(website=website).exists()
    base = f"/voice-agent/{website.id}"
    return [
        ChecklistItem(
            key="introduction_doc",
            label="Add the Introduction template",
            description="Same persona file the inbound agent uses — only needed once.",
            done=_has_intro_doc(website),
            cta_url=f"{base}/knowledge-base?template=introduction",
        ),
        ChecklistItem(
            key="sales_script",
            label="Add the Outbound Sales Script template",
            description=(
                "A structured script with opening, discovery, pitch, and objection "
                "handling. Edit it to match your product."
            ),
            done=_has_outbound_script(website),
            cta_url=f"{base}/knowledge-base?template=outbound_sales_script",
        ),
        ChecklistItem(
            key="from_number",
            label="Provision a caller-ID number",
            description=(
                "Add a phone number and connect it to a Telnyx outbound trunk. The "
                "AI will dial out from this number."
            ),
            done=has_outbound_number,
            cta_url=f"{base}/phone-numbers",
        ),
        ChecklistItem(
            key="first_campaign",
            label="Create your first campaign",
            description=(
                "Upload a CSV of leads, write a one-line welcome message, and start "
                "calling. You can also use the 'Call now' button for a single test call."
            ),
            done=has_campaign,
            cta_url=f"{base}/campaigns",
        ),
    ]


def setup_status(website) -> dict:
    inbound = inbound_checklist(website)
    outbound = outbound_checklist(website)

    def pct(items: Iterable[ChecklistItem]) -> int:
        items = list(items)
        if not items:
            return 0
        return int(round(100 * sum(1 for i in items if i.done) / len(items)))

    return {
        "inbound": {
            "label": "AI Receptionist (Inbound)",
            "description": (
                "Answer business calls automatically. The AI greets callers, "
                "answers questions from your knowledge base, books appointments, "
                "and creates todos for you when it can't."
            ),
            "progress": pct(inbound),
            "complete": all(i.done for i in inbound),
            "steps": [item.__dict__ for item in inbound],
        },
        "outbound": {
            "label": "AI Sales Caller (Outbound)",
            "description": (
                "Run outbound campaigns. Upload a list of leads, write a welcome "
                "line, and let the AI call them — using your sales script and FAQs "
                "to handle the conversation."
            ),
            "progress": pct(outbound),
            "complete": all(i.done for i in outbound),
            "steps": [item.__dict__ for item in outbound],
        },
    }
