"""Run a hired agent: gather data, reason with the LLM, persist + deliver.

A single LLM turn per run (no multi-step loop) — cheap and predictable. Token
usage is metered per-user automatically by the provider (role="agent").
"""
from __future__ import annotations

import json
import logging

from django.utils import timezone

from apps.agents.catalog import get_spec
from apps.agents.models import AgentAction, AgentInsight
from apps.agents.services import _json, delivery

logger = logging.getLogger("apps")

# Cap the gathered-data blob we hand the model so a noisy website can't blow
# the prompt budget for what is a secondary, low-cost operation.
_MAX_DATA_CHARS = 6000


def _brain_context(user, website, spec) -> str:
    """Best-effort RAG context. Never fails the run (embeddings may be absent)."""
    try:
        from apps.rag.services.retriever import retrieve_context_block

        return retrieve_context_block(
            user=user, website=website,
            query=f"{spec.domain} {getattr(website, 'name', '')}",
            top_k=4, max_chars=1500,
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("agent brain context failed: %s", exc)
        return ""


def _fallback_insight(spec, data: dict) -> dict:
    """Deterministic insight when no LLM provider is configured."""
    has = data.get("has_data")
    if has:
        summary = (
            f"{spec.name} pulled fresh data for your website. "
            "Connect an AI provider key to get a written analysis."
        )
    else:
        summary = (
            f"{spec.name} has no data yet. Run an audit / add knowledge so the "
            "agent has something to analyse."
        )
    return {
        "title": f"{spec.name}: daily update",
        "summary_markdown": summary,
        "key_points": [],
        "proposed_actions": [],
    }


def _build_prompt(spec, data: dict, brain: str) -> str:
    data_json = json.dumps(data, default=str)[:_MAX_DATA_CHARS]
    allowed = ", ".join(spec.allowed_action_types) or "(none)"
    parts = [
        f"DATA (today, JSON):\n{data_json}",
        f"\nALLOWED action_type values for proposed_actions: {allowed}",
    ]
    if brain:
        parts.append(f"\nCOMPANY KNOWLEDGE (for grounding):\n{brain}")
    parts.append("\nWrite today's update as STRICT JSON per the schema.")
    return "\n".join(parts)


def run_agent(hired_agent, *, deliver: bool = True) -> AgentInsight:
    """Execute one run for ``hired_agent`` and return the created insight."""
    spec = get_spec(hired_agent.agent_key)
    if spec is None:
        raise ValueError(f"Unknown agent_key: {hired_agent.agent_key}")

    user = hired_agent.user
    website = hired_agent.website

    data = spec.gatherer(user, website)
    brain = _brain_context(user, website, spec)

    from apps.llm_ranking.providers import get_provider, get_synthesis_provider

    provider = get_provider("claude") or get_synthesis_provider()
    if provider is None:
        parsed = _fallback_insight(spec, data)
    else:
        result = provider.query(
            _build_prompt(spec, data, brain),
            spec.system_prompt,
            user=user,
            website=website,
            audit_id=f"agent:{hired_agent.id}",
            role="agent",
            module="agents",
            # Runs are dispatched by the beat scheduler, not a click.
            extra_metadata={"actor": "system"},
        )
        parsed = _json.extract_object(getattr(result, "text", "") or "")
        if not parsed.get("title"):
            parsed = _fallback_insight(spec, data)

    insight = AgentInsight.objects.create(
        hired_agent=hired_agent,
        run_date=timezone.now().date(),
        title=str(parsed.get("title", ""))[:300],
        summary_markdown=str(parsed.get("summary_markdown", "")),
        data={"gathered": data, "key_points": parsed.get("key_points", [])},
        source_refs=_collect_source_refs(data),
    )

    _persist_proposed_actions(hired_agent, insight, spec, parsed.get("proposed_actions", []))

    hired_agent.last_run_at = timezone.now()
    hired_agent.consecutive_failures = 0
    hired_agent.last_failure_at = None
    hired_agent.save(update_fields=[
        "last_run_at", "consecutive_failures", "last_failure_at", "updated_at",
    ])

    if deliver:
        delivery.deliver(insight)
    return insight


def _collect_source_refs(data: dict) -> list:
    refs = []
    for key in ("current", "snapshots", "briefs", "alerts", "leads"):
        val = data.get(key)
        if isinstance(val, dict):
            refs.append(val)
        elif isinstance(val, list):
            refs.extend(val[:5])
    return refs[:10]


def _persist_proposed_actions(hired_agent, insight, spec, proposed) -> None:
    if not isinstance(proposed, list):
        return
    allowed = set(spec.allowed_action_types)
    for item in proposed[:3]:
        if not isinstance(item, dict):
            continue
        action_type = str(item.get("action_type", "")).strip()
        if action_type not in allowed:
            continue
        AgentAction.objects.create(
            hired_agent=hired_agent,
            insight=insight,
            action_type=action_type,
            title=str(item.get("title", action_type))[:300],
            params=item.get("params") or {},
        )
