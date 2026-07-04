"""The agent catalog.

Agent *types* are defined here in code (not the database), mirroring the
declarative pattern in ``core/integrations/registry.py``. A user "hires" one
of these (creating a ``HiredAgent`` row). Each spec wires a persona
(``system_prompt``), a data ``gatherer``, and the action types the agent is
allowed to propose.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from apps.agents.services import gatherers

# Action types an agent may propose. Kept intentionally small and internal for
# v1 (no external publishing). All execution is gated by human approval.
ACTION_INGEST_URL = "ingest_url"          # add a URL to the company brain (RAG)
ACTION_DRAFT_BRIEF = "draft_brief"        # create a ContentBrief to act on later
ACTION_NOTIFY = "notify"                  # raise an in-app notification/reminder


@dataclass(frozen=True)
class AgentSpec:
    key: str
    name: str
    tagline: str
    domain: str
    icon: str
    system_prompt: str
    gatherer: Callable[[object, object], dict]
    allowed_action_types: list[str] = field(default_factory=list)
    # Optional boolean PLAN_LIMITS key required to hire this agent. None = any plan.
    entitlement_key: str | None = None


_BASE_PERSONA = (
    "You are a focused growth analyst working inside FetchBot, a platform that "
    "measures how visible a business is inside AI assistants (ChatGPT, Claude, "
    "Gemini, Perplexity). You produce short, concrete, skimmable daily updates "
    "for a busy operator. Be specific, cite the numbers you were given, and "
    "never invent data you were not provided.\n\n"
    "Return STRICT JSON only, with this shape:\n"
    "{\n"
    '  "title": string,                // <= 80 chars, the headline of today\'s update\n'
    '  "summary_markdown": string,     // 2-5 short sentences / bullets, Slack-friendly\n'
    '  "key_points": [string],         // 1-4 bullet takeaways\n'
    '  "proposed_actions": [           // 0-3, only from the allowed action types\n'
    '     {"action_type": string, "title": string, "params": object}\n'
    "  ]\n"
    "}\n"
    "If there is no data yet, say so plainly and propose a setup action."
)


CATALOG: dict[str, AgentSpec] = {
    "visibility_analyst": AgentSpec(
        key="visibility_analyst",
        name="Visibility Analyst",
        tagline="Tracks how often AI assistants mention your brand and what moved.",
        domain="AI visibility / LLM ranking",
        icon="Brain",
        system_prompt=(
            _BASE_PERSONA + "\n\nYour focus: the latest LLM-ranking audit — overall "
            "visibility score, mention rate, average rank, and the change since the "
            "previous run. Call out wins and regressions and suggest one next step."
        ),
        gatherer=gatherers.visibility_analyst,
        allowed_action_types=[ACTION_NOTIFY, ACTION_DRAFT_BRIEF],
    ),
    "citation_hunter": AgentSpec(
        key="citation_hunter",
        name="Citation & Source Hunter",
        tagline="Finds which sources AI cites about you and where the gaps are.",
        domain="Citations / source influence",
        icon="Link",
        system_prompt=(
            _BASE_PERSONA + "\n\nYour focus: the sources/domains AI assistants cite "
            "when answering about this business and its space. Surface the most "
            "influential domains, notable new sources, and gaps worth targeting."
        ),
        gatherer=gatherers.citation_hunter,
        allowed_action_types=[ACTION_INGEST_URL, ACTION_NOTIFY],
    ),
    "content_strategist": AgentSpec(
        key="content_strategist",
        name="Content Strategist",
        tagline="Turns visibility and accuracy gaps into what to write next.",
        domain="Content studio / briefs",
        icon="FileText",
        system_prompt=(
            _BASE_PERSONA + "\n\nYour focus: the highest-impact open content briefs. "
            "Recommend which one or two to act on now and why, in plain language."
        ),
        gatherer=gatherers.content_strategist,
        allowed_action_types=[ACTION_DRAFT_BRIEF, ACTION_NOTIFY],
    ),
    "lead_scout": AgentSpec(
        key="lead_scout",
        name="Lead Scout",
        tagline="Summarises your highest-value visitors and what to do about them.",
        domain="Analytics / leads",
        icon="Users",
        system_prompt=(
            _BASE_PERSONA + "\n\nYour focus: the highest-scoring recent visitors. "
            "Summarise who is showing intent and suggest a follow-up."
        ),
        gatherer=gatherers.lead_scout,
        allowed_action_types=[ACTION_NOTIFY],
    ),
    "brand_watchdog": AgentSpec(
        key="brand_watchdog",
        name="Brand Watchdog",
        tagline="Flags inaccurate or risky things AI says about your brand.",
        domain="Brand vault / safety",
        icon="ShieldAlert",
        system_prompt=(
            _BASE_PERSONA + "\n\nYour focus: open safety alerts where an AI assistant "
            "said something inaccurate, outdated, or risky about the brand. "
            "Prioritise by severity and suggest how to correct the record."
        ),
        gatherer=gatherers.brand_watchdog,
        allowed_action_types=[ACTION_INGEST_URL, ACTION_DRAFT_BRIEF, ACTION_NOTIFY],
    ),
}


def get_spec(agent_key: str) -> AgentSpec | None:
    return CATALOG.get(agent_key)


def available_for(user) -> list[AgentSpec]:
    """Return the catalog specs the user's plan may hire.

    v1: every agent is available to every plan; the *number* of concurrently
    hired agents is what plan tiers gate (enforced at hire time via
    ``max_agents`` in PLAN_LIMITS). An ``entitlement_key`` can gate individual
    agents to higher tiers later.
    """
    from apps.billing.services import plan_limits

    specs = []
    for spec in CATALOG.values():
        if spec.entitlement_key and not plan_limits.check_feature(user, spec.entitlement_key):
            continue
        specs.append(spec)
    return specs
