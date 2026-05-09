"""Regex-based fallback extractor.

Pulls every plausible URL out of the LLM response text. Used as the
default for providers that don't return structured citations and as a
backstop for providers that do (so a URL mentioned inline but missing
from the structured list is still captured).
"""
from __future__ import annotations

import re
from typing import List

from apps.citations.services.extractors.base import BaseExtractor, CitationCandidate

# Match HTTP(S) URLs. Stops at whitespace and common punctuation that is
# unlikely to belong to the URL (closing brackets, trailing comma/period
# from a sentence, etc.). Conservative on the trailing char so we don't
# include the period at the end of "...visit https://example.com." but
# still keep slashes and trailing letters/digits.
_URL_RE = re.compile(
    r"https?://[^\s\]\)\>\,\;\"\'<]+[a-zA-Z0-9/_\-]"
)


class RegexExtractor(BaseExtractor):
    name = "regex"
    confidence = 0.6

    def extract(self, result) -> List[CitationCandidate]:
        text = getattr(result, "response_text", "") or ""
        if not text:
            return []
        out: List[CitationCandidate] = []
        seen: set[str] = set()
        for idx, match in enumerate(_URL_RE.finditer(text)):
            url = match.group(0)
            # Trim balanced trailing punctuation that the regex deliberately
            # left in so it could match URL paths ending in slashes.
            url = url.rstrip(".,);]>'\"")
            if url in seen:
                continue
            seen.add(url)
            out.append(
                CitationCandidate(
                    url=url,
                    extraction_method="regex",
                    confidence=self.confidence,
                    position=idx,
                )
            )
        return out
