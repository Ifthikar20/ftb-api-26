"""
Regions catalog for geo-segmented LLM ranking audits.

A region is a two-letter ISO country code plus a human label and the
prompt-flavour string we splice into prompts to bias the LLM toward
that geo's training-data examples.

Selecting a region affects three places in the pipeline:

  1. ``LLMRankingService.generate_prompts`` — appends a region hint
     to each prompt template ("... used by US companies").
  2. ``providers.perplexity.PerplexityProvider`` — passes the region
     to Perplexity's ``web_search_options.user_location`` so the
     web-grounded search retrieves region-appropriate sources.
  3. ``citation_geo.attribute_country`` — labels each citation URL
     with the country derived from its ccTLD; the per-audit
     ``citation_countries`` aggregate is then a region-of-origin
     footprint for the brands that ranked.
"""
from __future__ import annotations

from dataclasses import dataclass

REGION_GLOBAL = "global"
REGION_US = "us"
REGION_CA = "ca"
REGION_IN = "in"
REGION_UK = "uk"
REGION_DE = "de"
REGION_AU = "au"


@dataclass(frozen=True)
class Region:
    code: str
    label: str
    flavor: str           # spliced into prompts
    perplexity_country: str  # ISO-2 code passed to Perplexity user_location


REGIONS: dict[str, Region] = {
    REGION_GLOBAL: Region(REGION_GLOBAL, "Global", "", ""),
    REGION_US: Region(REGION_US, "United States",
                      "for US companies and customers", "US"),
    REGION_CA: Region(REGION_CA, "Canada",
                      "used by Canadian businesses", "CA"),
    REGION_IN: Region(REGION_IN, "India",
                      "popular in India", "IN"),
    REGION_UK: Region(REGION_UK, "United Kingdom",
                      "in the UK market", "GB"),
    REGION_DE: Region(REGION_DE, "Germany",
                      "used by German companies", "DE"),
    REGION_AU: Region(REGION_AU, "Australia",
                      "popular with Australian teams", "AU"),
}

# Broader country catalog. The original six above keep their hand-written
# flavours (tests depend on them); the rest are added generically. Each is
# keyed by its ISO-2 code (lower-case) and routes Perplexity web search to
# that country, so selecting e.g. Russia or Ukraine mimics a local user.
_EXTRA_COUNTRIES = [
    ("gb", "United Kingdom"), ("fr", "France"), ("es", "Spain"),
    ("it", "Italy"), ("nl", "Netherlands"), ("se", "Sweden"),
    ("ie", "Ireland"), ("ru", "Russia"), ("ua", "Ukraine"),
    ("pl", "Poland"), ("br", "Brazil"), ("mx", "Mexico"),
    ("ar", "Argentina"), ("jp", "Japan"), ("kr", "South Korea"),
    ("cn", "China"), ("sg", "Singapore"), ("hk", "Hong Kong"),
    ("ae", "United Arab Emirates"), ("sa", "Saudi Arabia"),
    ("za", "South Africa"), ("ng", "Nigeria"), ("id", "Indonesia"),
    ("ph", "Philippines"), ("my", "Malaysia"), ("th", "Thailand"),
    ("vn", "Vietnam"), ("tr", "Turkey"), ("il", "Israel"),
    ("nz", "New Zealand"), ("ch", "Switzerland"), ("at", "Austria"),
    ("be", "Belgium"), ("pt", "Portugal"), ("no", "Norway"),
    ("dk", "Denmark"), ("fi", "Finland"),
]
for _code, _label in _EXTRA_COUNTRIES:
    REGIONS.setdefault(
        _code, Region(_code, _label, f"popular in {_label}", _code.upper()),
    )

REGION_CHOICES = [(r.code, r.label) for r in REGIONS.values()]


def get_region(code: str) -> Region:
    """Lookup a region by code; falls back to GLOBAL for unknown codes."""
    return REGIONS.get((code or "").lower(), REGIONS[REGION_GLOBAL])


def region_for_country(code: str) -> str:
    """Map an ISO-2 country code to a supported region code (else GLOBAL).

    ``GB``/``UK`` both resolve to the British region. Any country present in
    the catalog routes to itself; unknown codes fall back to GLOBAL.
    """
    c = (code or "").strip().lower()
    if c == "uk":
        c = "gb"
    return c if c in REGIONS and c != REGION_GLOBAL else REGION_GLOBAL


def supported_countries() -> list[dict]:
    """Country options for the Add Prompt location picker.

    Returns ``[{"code": ISO-2, "name": label}]`` (no GLOBAL), de-duplicated
    by ISO-2 and sorted by name, so backend and frontend stay in sync.
    """
    by_iso: dict[str, str] = {}
    for r in REGIONS.values():
        iso = r.perplexity_country
        if iso:
            by_iso[iso] = r.label
    return sorted(
        ({"code": iso, "name": name} for iso, name in by_iso.items()),
        key=lambda c: c["name"],
    )


def flavor_prompt(prompt_text: str, region_code: str) -> str:
    """
    Append the region's prompt flavour to a prompt without breaking the
    sentence. ``GLOBAL`` returns the prompt unchanged.

    We append rather than rewrite so the intent type / placeholder
    semantics from the prompt library stay intact.
    """
    region = get_region(region_code)
    if not region.flavor:
        return prompt_text
    text = prompt_text.rstrip()
    # Drop trailing punctuation, splice in the flavour, re-add a question mark
    # if the original ended in one. Keeps "What are the best X?" → "What
    # are the best X for US companies and customers?" reading naturally.
    ends_q = text.endswith("?")
    if ends_q:
        text = text[:-1].rstrip()
    if text.endswith((".", "!")):
        text = text[:-1].rstrip()
    text = f"{text} {region.flavor}"
    return f"{text}?" if ends_q else f"{text}."
