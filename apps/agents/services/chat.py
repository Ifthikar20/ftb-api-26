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
                        thread_ts: str = "",
                        context_block: str = "") -> AgentMessage:
    """Persist the user message, generate a reply, persist + return the reply.

    ``context_block`` is optional per-turn grounding (e.g. the chat-command
    fact pack of live metrics). It is injected into the generation prompt
    only - never persisted to the transcript - so the stored conversation
    stays clean and stale facts are not replayed on later turns.
    """
    AgentMessage.objects.create(
        hired_agent=hired_agent, role=AgentMessage.ROLE_USER,
        text=text, channel=channel, thread_ts=thread_ts,
    )

    spec = get_spec(hired_agent.agent_key)
    reply_text = _generate_reply(hired_agent, spec, text, context_block)

    return AgentMessage.objects.create(
        hired_agent=hired_agent, role=AgentMessage.ROLE_AGENT,
        text=reply_text, channel=channel, thread_ts=thread_ts,
    )


def _generate_reply(hired_agent, spec, text: str, context_block: str = "") -> str:
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
        + (f"{context_block}\n\n" if context_block else "")
        + f"CONVERSATION SO FAR:\n{convo}\n\n"
        f"The user just said: {text}\n\n"
        "Reply concisely and helpfully in plain text (no JSON)."
    )
    system_prompt = spec.system_prompt
    if context_block:
        system_prompt += (
            "\n\nThe prompt includes a block of live account facts, which "
            "also carries the account's saved prompts (listed most recent "
            "first - 'my most recent prompt' means the first entry of that "
            "list) and content from the latest completed visibility audit. "
            "Answer metric questions strictly from those facts and the "
            "other provided context; never fabricate numbers. If the "
            "question needs data that is not tracked there, say plainly "
            "what is missing and point the user at the FetchBot command or "
            "dashboard page that has it."
        )
    result = provider.query(
        prompt, system_prompt,
        user=hired_agent.user, website=hired_agent.website,
        audit_id=f"agent_chat:{hired_agent.id}", role="agent_chat",
        module="agents",
    )
    reply = (getattr(result, "text", "") or "").strip()
    return reply or "I don't have an answer for that yet."
