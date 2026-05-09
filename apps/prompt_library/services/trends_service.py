"""Google Trends fetcher for IndustryTrend rows.

Uses :pkg:`pytrends` (already in ``requirements/base.txt``). Trends has no
official API and pytrends gets throttled aggressively, so:

* We only call Trends at the *industry* level — never per-prompt.
* Results are cached on :class:`apps.prompt_library.models.IndustryTrend`
  for ``CACHE_TTL`` (24h by default).
* Failures are caught and recorded on ``last_error``; callers continue
  with whatever cached data already exists.

Network access is optional: if pytrends raises (offline dev box, blocked
egress, 429), the caller still gets the previously cached row, or an
empty payload on a cold cache.
"""
from __future__ import annotations

import logging
from datetime import timedelta

from django.utils import timezone

from apps.prompt_library.models import Industry, IndustryTrend

logger = logging.getLogger(__name__)

CACHE_TTL = timedelta(hours=24)


# Slug → keyword we feed to Google Trends. The industry name is often too
# generic (e.g. "SaaS / DevTools") so we map to a head-noun a person would
# actually search for.
KEYWORD_OVERRIDES = {
    "saas-crm": "CRM software",
    "saas-analytics": "product analytics",
    "saas-devtools": "developer tools",
    "e-commerce-dtc": "Shopify",
    "e-commerce-marketplaces": "Amazon FBA",
    "education-edtech": "online learning",
    "financial-services": "personal finance",
    "food-beverage": "meal kit",
    "healthcare-telemedicine": "telehealth",
    "hospitality-travel": "travel rewards",
    "insurance": "car insurance",
    "legal-services": "online lawyer",
    "local-services-hvac": "HVAC repair",
    "local-services-health-wellness": "personal trainer",
    "local-services-home-services": "plumber",
    "manufacturing-industrial": "ERP software",
    "media-publishing": "newsletter platform",
    "nonprofit": "fundraising platform",
    "professional-services-consulting": "fractional CFO",
    "real-estate": "mortgage rates",
}

# A small set of country names so we can render flags / human labels.
_COUNTRY_NAMES = {
    "US": "United States", "GB": "United Kingdom", "CA": "Canada",
    "AU": "Australia", "DE": "Germany", "FR": "France",
    "PL": "Poland", "RU": "Russia", "IN": "India",
    "BR": "Brazil", "JP": "Japan", "KR": "South Korea",
    "MX": "Mexico", "ES": "Spain", "IT": "Italy",
    "NL": "Netherlands", "SE": "Sweden", "NO": "Norway",
    "ZA": "South Africa", "NG": "Nigeria", "EG": "Egypt",
    "AE": "United Arab Emirates", "SA": "Saudi Arabia",
    "TR": "Turkey", "AR": "Argentina", "CL": "Chile",
    "CO": "Colombia", "PE": "Peru", "VN": "Vietnam",
    "ID": "Indonesia", "TH": "Thailand", "PH": "Philippines",
    "MY": "Malaysia", "SG": "Singapore", "NZ": "New Zealand",
    "IE": "Ireland", "BE": "Belgium", "CH": "Switzerland",
    "AT": "Austria", "DK": "Denmark", "FI": "Finland",
    "PT": "Portugal", "GR": "Greece", "CZ": "Czechia",
    "RO": "Romania", "UA": "Ukraine", "IL": "Israel",
    "PK": "Pakistan", "BD": "Bangladesh", "KE": "Kenya",
}


def _country_name(code: str) -> str:
    return _COUNTRY_NAMES.get(code.upper(), code.upper())


def get_trend_payload(industry: Industry) -> dict:
    """Return cached IndustryTrend data, refreshing if older than CACHE_TTL.

    Returns the same shape regardless of pytrends success so the API
    response is uniform.
    """
    trend, _ = IndustryTrend.objects.get_or_create(industry=industry)

    fresh = (
        trend.refreshed_at is not None
        and trend.refreshed_at >= timezone.now() - CACHE_TTL
        and trend.interest_over_time
    )
    if not fresh:
        try:
            _refresh(trend)
        except Exception as exc:  # noqa: BLE001 — pytrends raises bare Exception
            logger.warning("pytrends refresh failed for %s: %s", industry.slug, exc)
            trend.last_error = str(exc)[:500]
            trend.save(update_fields=["last_error", "updated_at"])

    return {
        "industry": {"slug": industry.slug, "name": industry.name},
        "keyword": trend.keyword_used or KEYWORD_OVERRIDES.get(industry.slug) or industry.name,
        "interest_over_time": trend.interest_over_time or [],
        "top_regions": trend.top_regions or [],
        "refreshed_at": trend.refreshed_at.isoformat() if trend.refreshed_at else None,
        "stale": not fresh,
        "error": trend.last_error or None,
    }


def _refresh(trend: IndustryTrend) -> None:
    """Hit pytrends and store the result on ``trend``."""
    from pytrends.request import TrendReq  # local import — heavy module

    keyword = KEYWORD_OVERRIDES.get(trend.industry.slug) or trend.industry.name

    pytrends = TrendReq(hl="en-US", tz=0, timeout=(4, 12))
    pytrends.build_payload([keyword], timeframe="today 12-m", geo="")

    iot_df = pytrends.interest_over_time()
    interest_over_time: list[dict] = []
    if iot_df is not None and not iot_df.empty:
        col = keyword if keyword in iot_df.columns else iot_df.columns[0]
        for ts, val in iot_df[col].items():
            interest_over_time.append({
                "week": ts.date().isoformat(),
                "value": int(val) if val == val else 0,  # NaN-safe
            })

    region_df = pytrends.interest_by_region(resolution="COUNTRY", inc_low_vol=False)
    top_regions: list[dict] = []
    if region_df is not None and not region_df.empty:
        col = keyword if keyword in region_df.columns else region_df.columns[0]
        # Pytrends indexes by full country name; we need ISO-2 codes for
        # rendering flags. Use the geographic mapping pytrends ships with.
        for name, val in region_df[col].sort_values(ascending=False).head(8).items():
            try:
                v = int(val)
            except (TypeError, ValueError):
                continue
            if v <= 0:
                continue
            top_regions.append({
                "code": _name_to_code(name),
                "name": name,
                "value": v,
            })

    trend.keyword_used = keyword
    trend.interest_over_time = interest_over_time
    trend.top_regions = top_regions
    trend.refreshed_at = timezone.now()
    trend.last_error = ""
    trend.save(update_fields=[
        "keyword_used",
        "interest_over_time",
        "top_regions",
        "refreshed_at",
        "last_error",
        "updated_at",
    ])


# Reverse map for the small subset we care about. pytrends uses full
# names; we just want flags so this is best-effort.
_NAME_TO_CODE = {v: k for k, v in _COUNTRY_NAMES.items()}


def _name_to_code(name: str) -> str:
    if name in _NAME_TO_CODE:
        return _NAME_TO_CODE[name]
    # Pytrends sometimes returns "United States" / "Czechia" exactly.
    # Anything else, fall back to the first two uppercase letters.
    return name[:2].upper()
