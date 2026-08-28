"""Retention windows, resolved in one place.

Every window is declared in settings so the numbers we publish on
/what-we-track have a single source of truth. This module exists for the
cases where the window is not a plain constant -- currently just the Gemini
grounding cap, which depends on a feature flag rather than on configuration.
"""
from __future__ import annotations

from django.conf import settings

# LLMRankingResult.provider stores "gemini" (models.PROVIDER_GEMINI).
# Note AITokenUsage.provider stores "google" for the same vendor -- the two
# models disagree, so anything matching on vendor must pick the right one.
GEMINI_PROVIDER = "gemini"


def effective_llm_result_retention_days(provider: str | None = None) -> int:
    """Days an LLMRankingResult of this provider may be kept.

    Normally LLM_RESULT_RETENTION_DAYS. The exception is Gemini while
    LLM_WEBSEARCH_ENABLED is on: that switches Gemini to the
    google_search_retrieval tool, and Gemini's additional terms only permit
    storing the text of a Grounded Result for thirty days -- excluding the
    links, and only to evaluate and optimise how it is displayed. Keeping
    those rows for the normal two years would breach that grant, so the
    window collapses to the cap whenever grounding is live.

    Passing provider=None returns the general window, which is what the
    pruner uses for every non-Gemini row.
    """
    configured = int(settings.LLM_RESULT_RETENTION_DAYS)

    if provider != GEMINI_PROVIDER:
        return configured
    if not getattr(settings, "LLM_WEBSEARCH_ENABLED", False):
        # Ungrounded Gemini output carries no special storage term.
        return configured

    return min(configured, int(settings.GROUNDED_RESULT_MAX_RETENTION_DAYS))


def grounded_links_may_be_stored(provider: str | None = None) -> bool:
    """False when the provider's terms exclude links from what we may keep.

    Gemini's grounding terms permit storing the Grounded Result text but
    explicitly exclude the links. Callers that persist citations should skip
    them for these rows rather than relying on the pruner to catch up.
    """
    if provider != GEMINI_PROVIDER:
        return True
    return not getattr(settings, "LLM_WEBSEARCH_ENABLED", False)
