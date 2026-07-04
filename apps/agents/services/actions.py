"""Execute approved agent actions.

Only runs for actions in the ``approved`` state. v1 supports a small set of
internal, low-risk action types; richer "promote"/publish actions are a
follow-up once the content_studio publish adapters are rebuilt.
"""
from __future__ import annotations

import logging

from django.utils import timezone

from apps.agents.catalog import (
    ACTION_DRAFT_BRIEF,
    ACTION_INGEST_URL,
    ACTION_NOTIFY,
)
from apps.agents.models import AgentAction

logger = logging.getLogger("apps")


def execute_action(action: AgentAction) -> dict:
    """Execute an approved action; persist status + result. Returns the result."""
    if action.status != AgentAction.STATUS_APPROVED:
        return {"skipped": f"action not approved (status={action.status})"}

    action.status = AgentAction.STATUS_EXECUTING
    action.save(update_fields=["status", "updated_at"])

    handler = _HANDLERS.get(action.action_type)
    try:
        if handler is None:
            raise ValueError(f"Unknown action_type: {action.action_type}")
        result = handler(action)
        action.status = AgentAction.STATUS_DONE
    except Exception as exc:
        logger.warning("agent action %s failed: %s", action.id, exc)
        result = {"error": str(exc)}
        action.status = AgentAction.STATUS_FAILED

    action.result = result
    action.executed_at = timezone.now()
    action.save(update_fields=["status", "result", "executed_at", "updated_at"])
    return result


def _do_ingest_url(action: AgentAction) -> dict:
    """Add a URL to the company brain (RAG) via the existing ingest task."""
    params = action.params or {}
    url = (params.get("url") or "").strip()
    if not url:
        raise ValueError("ingest_url requires params.url")
    hired = action.hired_agent
    from apps.rag.tasks import ingest_url_task

    ingest_url_task.delay(
        user_id=str(hired.user_id),
        website_id=str(hired.website_id),
        url=url,
        kind=params.get("kind", "other"),
        title=params.get("title", ""),
    )
    return {"queued_ingest": url}


def _do_draft_brief(action: AgentAction) -> dict:
    """Create an open ContentBrief the user can later turn into a draft."""
    params = action.params or {}
    headline = (params.get("headline") or action.title or "").strip()
    if not headline:
        raise ValueError("draft_brief requires a headline")
    from apps.content_studio.models import ContentBrief

    brief = ContentBrief.objects.create(
        website=action.hired_agent.website,
        gap_type=params.get("gap_type", "visibility"),
        target_format=params.get("target_format", "blog"),
        headline=headline[:300],
        description=params.get("description", "")[:2000],
        status="open",
    )
    return {"content_brief_id": str(brief.id)}


def _do_notify(action: AgentAction) -> dict:
    """Raise an in-app notification/reminder for the user."""
    from apps.notifications.services.notification_service import NotificationService

    params = action.params or {}
    hired = action.hired_agent
    NotificationService.create(
        user=hired.user,
        notification_type="agent_action",
        title=(action.title or "Agent reminder")[:200],
        message=str(params.get("message", action.title))[:500],
        data={"hired_agent_id": str(hired.id), "action_id": str(action.id)},
        action_url=f"/agents/{hired.agent_key}?website={hired.website_id}",
    )
    return {"notified": True}


_HANDLERS = {
    ACTION_INGEST_URL: _do_ingest_url,
    ACTION_DRAFT_BRIEF: _do_draft_brief,
    ACTION_NOTIFY: _do_notify,
}
