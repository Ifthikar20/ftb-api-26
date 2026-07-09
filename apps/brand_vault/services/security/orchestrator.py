"""Orchestrates one Brand Security scan.

The orchestrator picks which agents to run (all enabled ones by default,
or an explicit subset), instantiates each from the registry, updates the
per-agent run status in the DB, and returns the aggregated stats. Alert
persistence happens inside each agent's ``scan()`` so this file only owns
the run bookkeeping.
"""
from __future__ import annotations

import logging
from datetime import timedelta

from django.utils import timezone

from apps.brand_vault.models import BrandSecurityAgent, SafetyAlert

from .registry import AGENTS, get_agent

logger = logging.getLogger("apps")


def ensure_agent_rows(website) -> list[BrandSecurityAgent]:
    """Make sure every registered agent has a row for this website.

    New agents added later automatically appear on existing websites the
    first time an orchestrator or API call touches the site.
    """
    rows: list[BrandSecurityAgent] = []
    for agent_id in AGENTS:
        row, _created = BrandSecurityAgent.objects.get_or_create(
            website=website, agent_id=agent_id,
        )
        rows.append(row)
    return rows


def run_agent(website, agent_id: str) -> dict:
    """Run one agent synchronously. Returns stats about the run."""
    agent = get_agent(agent_id)
    if agent is None:
        return {"agent_id": agent_id, "error": "unknown_agent", "alerts": 0}

    row, _ = BrandSecurityAgent.objects.get_or_create(
        website=website, agent_id=agent_id,
    )
    if not row.enabled:
        return {"agent_id": agent_id, "skipped": True, "alerts": 0}

    row.last_status = BrandSecurityAgent.STATUS_RUNNING
    row.last_error = ""
    row.save(update_fields=["last_status", "last_error", "updated_at"])

    alerts: list[SafetyAlert] = []
    try:
        alerts = agent.scan(website, row)
        status = BrandSecurityAgent.STATUS_IDLE
        error = ""
    except Exception as exc:
        logger.exception("Agent %s failed for website %s", agent_id, website.id)
        status = BrandSecurityAgent.STATUS_ERROR
        error = str(exc)[:600]

    row.last_run_at = timezone.now()
    row.last_status = status
    row.last_error = error
    row.next_run_at = _next_run_at(row)
    row.save(update_fields=[
        "last_run_at", "last_status", "last_error", "next_run_at", "updated_at",
    ])

    return {
        "agent_id": agent_id,
        "alerts": len(alerts),
        "status": status,
    }


def run_all_agents(website, *, only: list[str] | None = None) -> dict:
    """Run every enabled agent for the website. Returns aggregated stats."""
    ensure_agent_rows(website)
    per_agent: list[dict] = []
    for agent_id in AGENTS:
        if only is not None and agent_id not in only:
            continue
        per_agent.append(run_agent(website, agent_id))
    return {
        "website_id": str(website.id),
        "ran_at": timezone.now().isoformat(),
        "agents": per_agent,
        "total_alerts": sum(row.get("alerts", 0) for row in per_agent),
    }


def _next_run_at(agent_row: BrandSecurityAgent):
    """Schedule the next automatic run based on the agent's cadence."""
    now = timezone.now()
    delta = {
        BrandSecurityAgent.SCHEDULE_HOURLY: timedelta(hours=1),
        BrandSecurityAgent.SCHEDULE_DAILY: timedelta(days=1),
        BrandSecurityAgent.SCHEDULE_WEEKLY: timedelta(days=7),
    }.get(agent_row.schedule)
    if delta is None:
        return None
    return now + delta
