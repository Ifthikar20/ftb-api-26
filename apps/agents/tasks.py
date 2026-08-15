"""Celery tasks for hireable agents.

``dispatch_agent_runs`` is the beat-driven dispatcher (every 15 min); it mirrors
``apps.llm_ranking.tasks.dispatch_scheduled_audits`` — spend-cap gating,
in-flight skipping, auto-pause on repeated failure.
"""
from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task

logger = logging.getLogger("apps")

FREQUENCY_DELTAS = {
    "daily": timedelta(days=1),
    "weekly": timedelta(weeks=1),
}


@shared_task(name="apps.agents.tasks.dispatch_agent_runs")
def dispatch_agent_runs() -> None:
    """Enqueue a run for every active hired agent whose next_run_at has passed."""
    from django.utils import timezone

    from apps.agents.models import HiredAgent

    now = timezone.now()
    due = HiredAgent.objects.filter(
        is_active=True, next_run_at__lte=now,
    ).select_related("user")

    for agent in due:
        try:
            from core.ai_tracking import effective_ai_cap, month_to_date_cost

            cap = effective_ai_cap(agent.user)
            if cap > 0:
                if month_to_date_cost(agent.user) >= cap:
                    logger.warning(
                        "Skipping agent %s: user %s at AI spend cap.",
                        agent.id, agent.user_id,
                    )
                    _bump_next_run(agent, now)
                    continue

            run_hired_agent.delay(hired_agent_id=str(agent.id))
            _advance(agent, now)
        except Exception as exc:
            logger.error("dispatch_agent_runs failed for %s: %s", agent.id, exc)
            _bump_next_run(agent, now)


@shared_task(name="apps.agents.tasks.run_hired_agent", queue="ai")
def run_hired_agent(*, hired_agent_id: str) -> dict:
    """Execute one agent run (gather + reason + persist + deliver)."""
    from django.utils import timezone

    from apps.agents.models import HiredAgent
    from apps.agents.services.runner import run_agent

    try:
        agent = HiredAgent.objects.select_related("user", "website", "slack_connection").get(
            id=hired_agent_id
        )
    except HiredAgent.DoesNotExist:
        return {"ok": False, "error": "not_found"}

    try:
        insight = run_agent(agent)
        return {"ok": True, "insight_id": str(insight.id)}
    except Exception as exc:
        logger.exception("run_hired_agent(%s) failed: %s", hired_agent_id, exc)
        _record_failure(agent, timezone.now())
        return {"ok": False, "error": str(exc)}


@shared_task(name="apps.agents.tasks.execute_agent_action", queue="integrations")
def execute_agent_action(*, action_id: str) -> dict:
    """Execute a previously-approved agent action."""
    from apps.agents.models import AgentAction
    from apps.agents.services.actions import execute_action

    try:
        action = AgentAction.objects.select_related("hired_agent").get(id=action_id)
    except AgentAction.DoesNotExist:
        return {"ok": False, "error": "not_found"}
    result = execute_action(action)
    return {"ok": action.status == AgentAction.STATUS_DONE, "result": result}


# ── Schedule helpers (mirror llm_ranking dispatcher) ────────────────────────

def _advance(agent, now) -> None:
    delta = FREQUENCY_DELTAS.get(agent.frequency, timedelta(days=1))
    agent.last_run_at = now
    agent.next_run_at = now + delta
    agent.save(update_fields=["last_run_at", "next_run_at", "updated_at"])


def _bump_next_run(agent, now) -> None:
    delta = FREQUENCY_DELTAS.get(agent.frequency, timedelta(days=1))
    agent.next_run_at = now + delta
    agent.save(update_fields=["next_run_at", "updated_at"])


def _record_failure(agent, now) -> None:
    agent.consecutive_failures = (agent.consecutive_failures or 0) + 1
    agent.last_failure_at = now
    update_fields = ["consecutive_failures", "last_failure_at", "updated_at"]
    if agent.consecutive_failures >= (agent.auto_pause_threshold or 3):
        agent.is_active = False
        update_fields.append("is_active")
        logger.warning(
            "Auto-pausing agent %s after %d consecutive failures.",
            agent.id, agent.consecutive_failures,
        )
    agent.save(update_fields=update_fields)
