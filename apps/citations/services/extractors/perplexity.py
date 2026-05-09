"""Perplexity native citation extractor.

Perplexity's API returns a ``citations`` array on the response. The
ranking_service stores the structured analysis (which already carries
citations) on :attr:`LLMRankingResult.citations`. This extractor reads
that field and treats every URL there as a high-confidence native
citation.
"""
from __future__ import annotations

from typing import List

from apps.citations.services.extractors.base import BaseExtractor, CitationCandidate


class PerplexityNativeExtractor(BaseExtractor):
    name = "perplexity_native"
    confidence = 1.0

    def extract(self, result) -> List[CitationCandidate]:
        citations = getattr(result, "citations", None) or []
        if not citations:
            return []
        out: List[CitationCandidate] = []
        for idx, entry in enumerate(citations):
            url = ""
            title = ""
            snippet = ""
            if isinstance(entry, str):
                url = entry
            elif isinstance(entry, dict):
                url = entry.get("url") or entry.get("link") or entry.get("href") or ""
                title = entry.get("title") or entry.get("name") or ""
                snippet = entry.get("snippet") or entry.get("summary") or ""
            if not url:
                continue
            out.append(
                CitationCandidate(
                    url=url,
                    title=title[:500] if title else "",
                    snippet=snippet or "",
                    position=idx,
                    extraction_method="native",
                    confidence=self.confidence,
                )
            )
        return out
