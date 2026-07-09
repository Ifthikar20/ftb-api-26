"""Registry of Brand Security agents.

Import each agent class here and register it in ``AGENTS`` keyed by its
``agent_id``. The API views read this registry to expose per-agent metadata
(name, tagline, colour, sources) and the orchestrator uses it to instantiate
the classes for each scan.
"""
from __future__ import annotations

from .agents.impersonation import ImpersonationAgent
from .agents.llm_truth import LLMTruthAgent
from .agents.narrative_watch import NarrativeWatchAgent
from .agents.sentiment_pulse import SentimentPulseAgent
from .agents.serp_reputation import SerpReputationAgent
from .base import BaseSecurityAgent

AGENTS: dict[str, type[BaseSecurityAgent]] = {
    NarrativeWatchAgent.agent_id: NarrativeWatchAgent,
    LLMTruthAgent.agent_id: LLMTruthAgent,
    SerpReputationAgent.agent_id: SerpReputationAgent,
    SentimentPulseAgent.agent_id: SentimentPulseAgent,
    ImpersonationAgent.agent_id: ImpersonationAgent,
}


def get_agent(agent_id: str) -> BaseSecurityAgent | None:
    """Instantiate an agent by id. Returns None if the id is unknown."""
    cls = AGENTS.get(agent_id)
    return cls() if cls else None


def agent_catalog() -> list[dict]:
    """Static metadata for all registered agents, used by the UI."""
    return [
        {
            "agent_id": cls.agent_id,
            "display_name": cls.display_name,
            "tagline": cls.tagline,
            "color": cls.color,
            "sources": list(cls.sources),
        }
        for cls in AGENTS.values()
    ]
