"""Base citation extractor.

Each extractor inspects an :class:`LLMRankingResult` and returns a flat
list of :class:`CitationCandidate` records. Extractors are pure with
respect to the database — persistence happens in the orchestrator
(``extraction_service.extract_for_result``).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CitationCandidate:
    url: str
    title: str = ""
    snippet: str = ""
    position: int | None = None
    extraction_method: str = "regex"
    confidence: float = 1.0
    extra: dict = field(default_factory=dict)


class BaseExtractor:
    """Subclasses override :meth:`extract`. Stateless by convention."""

    name: str = "base"

    def extract(self, result) -> list[CitationCandidate]:  # pragma: no cover
        raise NotImplementedError
