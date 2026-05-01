"""
Competitor name normalisation.

LLM responses surface the same brand under many surface forms — "Mixpanel",
"mixpanel", "Mixpanel Inc.", "Mixpanel.com". Without normalisation each one
becomes a separate row in the citation-share denominator and the brand ranking,
inflating the count and pushing your own brand down the list.

This module exposes one entry point — `canonical_name(raw)` — that callers use
when grouping competitor mentions. Pure string handling, no external deps.
"""
from __future__ import annotations

import re

# Generic suffixes that don't change the brand identity.
_LEGAL_SUFFIXES = (
    "inc", "inc.", "incorporated",
    "llc", "llc.", "ltd", "ltd.", "limited",
    "co", "co.", "corp", "corp.", "corporation",
    "gmbh", "ag", "sa", "plc", "bv",
)

_TLD_PATTERN = re.compile(r"\.(com|io|ai|co|net|org|app|dev|tech|cloud)$", re.IGNORECASE)
_NON_WORD = re.compile(r"[^a-z0-9]+")
_MULTI_SPACE = re.compile(r"\s+")


def canonical_name(raw: str) -> str:
    """
    Return a normalised lookup key for a brand name.

    Examples:
        canonical_name("Mixpanel")        -> "mixpanel"
        canonical_name(" mixpanel.com ")  -> "mixpanel"
        canonical_name("Mixpanel Inc.")   -> "mixpanel"
        canonical_name("HubSpot CRM")     -> "hubspot crm"
        canonical_name("")                -> ""
    """
    if not raw:
        return ""
    name = raw.strip().lower()
    name = _TLD_PATTERN.sub("", name)
    # Drop trailing legal suffix if present (after a space or comma).
    parts = re.split(r"[,\s]+", name)
    while parts and parts[-1].rstrip(".").rstrip(",") in _LEGAL_SUFFIXES:
        parts.pop()
    name = " ".join(parts)
    # Collapse punctuation; keep alphanumerics and a single space.
    name = _NON_WORD.sub(" ", name)
    name = _MULTI_SPACE.sub(" ", name).strip()
    return name


def display_name(raw: str) -> str:
    """Best-effort display label preserving the user-visible casing."""
    if not raw:
        return ""
    return raw.strip()


# Minimum mentions for a competitor to be included in the ranked list.
# Filters out one-off LLM hallucinations from the citation-share denominator.
MIN_MENTIONS_FOR_RANKING = 2
