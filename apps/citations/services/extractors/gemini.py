"""Gemini grounding-chunk extractor.

Gemini returns ``groundingChunks`` on tool-grounded responses. Each chunk
typically has shape ``{"web": {"uri": ..., "title": ...}}``. The
ranking_service may flatten them onto :attr:`LLMRankingResult.citations`
(uniform shape) or persist a raw payload — this extractor handles both.
"""
from __future__ import annotations

from typing import Iterable, List

from apps.citations.services.extractors.base import BaseExtractor, CitationCandidate


def _iter_grounding_chunks(payload) -> Iterable[dict]:
    if not payload:
        return []
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        if "groundingChunks" in payload:
            return payload["groundingChunks"]
        if "grounding_chunks" in payload:
            return payload["grounding_chunks"]
    return []


class GeminiGroundingExtractor(BaseExtractor):
    name = "gemini_grounding"
    confidence = 1.0

    def extract(self, result) -> List[CitationCandidate]:
        # Look for grounding payload in common locations. The
        # ranking_service stores the structured citation list on .citations
        # — Gemini chunks may be flattened into that list, or we may have
        # a raw payload buried in an extension hook in the future.
        out: List[CitationCandidate] = []
        seen: set[str] = set()

        chunks = _iter_grounding_chunks(getattr(result, "grounding_chunks", None))
        for idx, chunk in enumerate(chunks):
            if not isinstance(chunk, dict):
                continue
            web = chunk.get("web") or chunk.get("retrievedContext") or {}
            url = web.get("uri") or web.get("url") or ""
            title = web.get("title") or ""
            if not url or url in seen:
                continue
            seen.add(url)
            out.append(
                CitationCandidate(
                    url=url, title=title[:500],
                    position=idx,
                    extraction_method="grounding",
                    confidence=self.confidence,
                )
            )

        # Fall back to the structured citations field — same shape as the
        # Perplexity extractor's input. This means a Gemini result that
        # already had its grounding chunks normalised onto .citations is
        # captured here without provider-specific code paths upstream.
        for idx, entry in enumerate(getattr(result, "citations", []) or []):
            url = ""
            title = ""
            if isinstance(entry, str):
                url = entry
            elif isinstance(entry, dict):
                url = entry.get("url") or entry.get("uri") or ""
                title = entry.get("title") or ""
            if not url or url in seen:
                continue
            seen.add(url)
            out.append(
                CitationCandidate(
                    url=url, title=title[:500],
                    position=idx,
                    extraction_method="grounding",
                    confidence=self.confidence,
                )
            )
        return out
