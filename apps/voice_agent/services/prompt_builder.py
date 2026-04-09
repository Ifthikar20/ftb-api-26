"""
Voice agent system prompt builder.

Merges the per-website AgentConfig prompt with optional business_context and
all active AgentContextDocument rows into a single string that gets sent to
the upstream voice provider (Retell, LiveKit, etc.) as the agent's system
prompt. This is the single source of truth — every code path that pushes a
prompt upstream MUST use this function so callers always get the latest KB.
"""

import logging

from apps.voice_agent.models import AgentConfig, AgentContextDocument

logger = logging.getLogger("apps")

# Cap on the merged system prompt fed to the live LLM. Prompt size is the
# single biggest lever on time-to-first-token: 8k chars (~2k tokens) lands
# under 800ms TTFT on most models, 20k chars often pushed it past 2s. If you
# need to surface more knowledge to the agent, prefer adding more focused
# AgentContextDocument rows over fattening a single doc.
MAX_PROMPT_CHARS = 8000


def build_retell_system_prompt(agent_config: AgentConfig) -> str:
    """Return the merged system prompt for an agent's website.

    Order:
        1. agent_config.system_prompt        (the base persona / instructions)
        2. agent_config.business_context     (free-form markdown on the config)
        3. All active AgentContextDocument rows for the website, sorted
           by (sort_order, created_at), each rendered as `## {title}\n{content}`.

    Output is truncated to MAX_PROMPT_CHARS to stay safely under provider
    prompt limits; truncation is logged so the UI/operator can react.
    """
    parts: list[str] = []

    base = (agent_config.system_prompt or "").strip()
    if base:
        parts.append(base)

    business_context = (agent_config.business_context or "").strip()
    if business_context:
        parts.append(business_context)

    docs = AgentContextDocument.objects.filter(
        website=agent_config.website,
        is_active=True,
    ).order_by("sort_order", "created_at")

    rendered_docs: list[str] = []
    for doc in docs:
        title = (doc.title or "Untitled").strip()
        content = (doc.content or "").strip()
        if not content:
            continue
        rendered_docs.append(f"## {title}\n{content}")

    if rendered_docs:
        parts.append("# Knowledge Base\n\n" + "\n\n".join(rendered_docs))

    merged = "\n\n".join(parts)

    if len(merged) > MAX_PROMPT_CHARS:
        logger.warning(
            "voice_agent.prompt_truncated",
            extra={
                "website_id": str(agent_config.website_id),
                "original_chars": len(merged),
                "limit": MAX_PROMPT_CHARS,
            },
        )
        merged = merged[:MAX_PROMPT_CHARS]

    return merged
