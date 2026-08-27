"""Shared helpers for OpenAI-compatible Responses API providers.

OpenAI and xAI both expose web search through the Responses API: the
response's ``output`` list holds ``web_search_call`` items (the queries
the model ran) and ``message`` items whose ``output_text`` content parts
carry ``annotations`` — ``url_citation`` entries naming the exact source
behind each cited span. This module turns that structure into the flat,
ordered URL list ProviderResult.citations expects.

Every read tolerates both typed SDK objects and plain dicts: pinned SDK
versions parse unknown-to-them fields as dicts (the same trap the Claude
provider hit), and test doubles are dicts too.
"""
from __future__ import annotations

MAX_CITATIONS = 20


def _get(item, key, default=None):
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def extract_responses_citations(resp) -> list[str]:
    """Ordered, deduped source URLs from a Responses API response.

    Cited pages (url_citation annotations, in answer order) come first;
    a provider-level ``citations`` list of URL strings (xAI's legacy
    shape) is appended after. Capped at MAX_CITATIONS.
    """
    urls: list[str] = []
    seen: set[str] = set()

    def _add(url) -> None:
        if isinstance(url, str) and url and url not in seen and len(urls) < MAX_CITATIONS:
            seen.add(url)
            urls.append(url)

    for item in _get(resp, "output", None) or []:
        if _get(item, "type") != "message":
            continue
        for part in _get(item, "content", None) or []:
            if _get(part, "type") != "output_text":
                continue
            for ann in _get(part, "annotations", None) or []:
                if _get(ann, "type") == "url_citation":
                    _add(_get(ann, "url"))

    for url in _get(resp, "citations", None) or []:
        _add(url)

    return urls
