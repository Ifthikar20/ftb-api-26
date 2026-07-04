"""Two-way chat with a hired agent (in-app in Phase A; Slack in Phase B).

Each turn grounds the reply in the agent persona, recent insights, the last
few messages, and the company brain (RAG).
"""
from __future__ import annotations

import logging

from apps.agents.catalog import get_spec
from apps.agents.models import AgentInsight, AgentMessage

logger = logging.getLogger("apps")

_HISTORY_LIMIT = 8


def _recent_context(hired_agent) -> str:
    parts = []
    latest = (
        AgentInsight.objects.filter(hired_agent=hired_agent)
        .order_by("-created_at")
        .values("title", "summary_markdown")
        .first()
    )
    if latest:
        parts.append(
            f"YOUR LAST UPDATE:\n{latest['title']}\n{latest['summary_markdown']}"
        )
    try:
        from apps.rag.services.retriever import retrieve_context_block

        spec = get_spec(hired_agent.agent_key)
        brain = retrieve_context_block(
            user=hired_agent.user, website=hired_agent.website,
            query=spec.domain if spec else hired_agent.agent_key,
            top_k=3, max_chars=1200,
        )
        if brain:
            parts.append(brain)
    except Exception:  # pragma: no cover - defensive
        pass
    return "\n\n".join(parts)


def handle_user_message(hired_agent, text: str, *, channel: str = "in_app",
                        thread_ts: str = "") -> AgentMessage:
    """Persist the user message, generate a reply, persist + return the reply."""
    AgentMessage.objects.create(
        hired_agent=hired_agent, role=AgentMessage.ROLE_USER,
        text=text, channel=channel, thread_ts=thread_ts,
    )

    spec = get_spec(hired_agent.agent_key)
    reply_text = _generate_reply(hired_agent, spec, text)

    return AgentMessage.objects.create(
        hired_agent=hired_agent, role=AgentMessage.ROLE_AGENT,
        text=reply_text, channel=channel, thread_ts=thread_ts,
    )


def _generate_reply(hired_agent, spec, text: str) -> str:
    from apps.llm_ranking.providers import get_provider, get_synthesis_provider

    provider = get_provider("claude") or get_synthesis_provider()
    if provider is None or spec is None:
        return (
            "I can't reach my reasoning model right now. Once an AI provider key "
            "is configured I'll answer in context."
        )

    history = list(
        AgentMessage.objects.filter(hired_agent=hired_agent)
        .order_by("-created_at")
        .values("role", "text")[:_HISTORY_LIMIT]
    )
    history.reverse()
    convo = "\n".join(f"{m['role']}: {m['text']}" for m in history)

    prompt = (
        f"{_recent_context(hired_agent)}\n\n"
        f"CONVERSATION SO FAR:\n{convo}\n\n"
        f"The user just said: {text}\n\n"
        "Reply concisely and helpfully in plain text (no JSON)."
    )
    result = provider.query(
        prompt, spec.system_prompt,
        user=hired_agent.user, website=hired_agent.website,
        audit_id=f"agent_chat:{hired_agent.id}", role="agent_chat",
    )
    reply = (getattr(result, "text", "") or "").strip()
    return reply or "I don't have an answer for that yet."
