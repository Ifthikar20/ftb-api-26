"""LLM-assisted citation extractor.

For providers that don't return structured citations and whose responses
contain only implicit references (e.g. "according to a recent report by
Forrester"), we can ask a small Claude/Llama model to extract them. This
is a stub that returns no candidates by default; the call site will
short-circuit when no API key is configured. The contract is preserved
so the orchestrator code path is exercised in tests.
"""
from __future__ import annotations

from apps.citations.services.extractors.base import BaseExtractor, CitationCandidate


class LLMAssistedExtractor(BaseExtractor):
    name = "llm_assisted"
    confidence = 0.7

    def __init__(self, *, enabled: bool = False):
        # Disabled by default — wiring the provider call adds latency and
        # cost. Enable per-call from the orchestrator when a feature flag
        # explicitly opts in.
        self.enabled = enabled

    def extract(self, result) -> list[CitationCandidate]:
        if not self.enabled:
            return []
        # Intentionally a no-op until the meta-prompt + provider routing
        # is wired up. Returning [] keeps the orchestrator's union/dedup
        # logic exercised without making external network calls.
        return []
