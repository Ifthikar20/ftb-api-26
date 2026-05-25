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

REGION_CHOICES = [(r.code, r.label) for r in REGIONS.values()]


def get_region(code: str) -> Region:
    """Lookup a region by code; falls back to GLOBAL for unknown codes."""
    return REGIONS.get((code or "").lower(), REGIONS[REGION_GLOBAL])


# ISO-2 country code (as picked in the Add Prompt modal) -> region code.
# Note the UK uses region code "uk" while its ISO-2 is "GB".
_COUNTRY_TO_REGION = {
    "US": REGION_US, "CA": REGION_CA, "IN": REGION_IN,
    "GB": REGION_UK, "UK": REGION_UK, "DE": REGION_DE, "AU": REGION_AU,
}


def region_for_country(code: str) -> str:
    """Map an ISO-2 country code to a supported region code (else GLOBAL)."""
    return _COUNTRY_TO_REGION.get((code or "").upper(), REGION_GLOBAL)


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
