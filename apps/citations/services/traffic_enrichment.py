"""Join the URLs dashboard to real traffic.

The Sources > URLs page counts LLM retrievals; on its own that never
answers "what does this mean for my traffic". This module closes the loop
by attaching, to every cited URL that belongs to the user's own site:

* Google Search Console performance for the same window (clicks,
  impressions, impression-weighted average position) from the nightly
  ``GscPageStat`` sync, and
* AI-referred visits measured by the tracking pixel — pageviews whose
  session was classified ``medium="ai"`` (arrived from ChatGPT,
  Perplexity, Claude and friends).

Everything is computed on read from already-indexed tables; there are no
new columns and no snapshots. The three URL vocabularies (citations,
GSC's canonical page URLs, the pixel's raw ``location.href``) disagree on
scheme, ``www.`` and tracking params, so every join goes through
:func:`traffic_match_key`.
"""
from __future__ import annotations

import logging
from collections import Counter, defaultdict
from datetime import date

from apps.citations.services.url_normalizer import normalize_url

logger = logging.getLogger("apps")

# Enrichment guardrails: the your-site row set is tiny in practice, and
# AI-referred pageviews are a small slice of PageEvent — but both caps
# keep a pathological tenant from turning the page into a table scan.
MAX_ENRICHED_ROWS = 200
MAX_AI_PAGEVIEWS = 25_000

# Session.source -> display label, mirroring analytics_service's
# get_ai_traffic_summary so the two surfaces never disagree on names.
AI_PROVIDER_LABELS = {
    "chatgpt": "ChatGPT",
    "claude": "Claude",
    "gemini": "Gemini",
    "perplexity": "Perplexity",
    "copilot": "Copilot",
    "meta-ai": "Meta AI",
    "poe": "Poe",
    "you": "You.com",
}


def traffic_match_key(url: str) -> str:
    """Canonical join key across citations, GSC pages and pixel URLs.

    ``normalize_url`` (the single source of truth for "same URL") keeps
    the scheme and ``www.``; GSC canonicals usually carry both while
    citations often do not, so the key additionally drops the scheme and
    a leading ``www.``.
    """
    normalized, host, _ = normalize_url(url or "")
    if not normalized or not host:
        return ""
    key = normalized.split("://", 1)[-1]
    if key.startswith("www."):
        key = key[4:]
    return key.lower()


def _gsc_integration(website):
    from apps.websites.models import Integration

    integration = Integration.objects.filter(website=website, type="gsc").first()
    return bool(
        integration and (integration.access_token or integration.refresh_token),
    )


def _gsc_by_key(website, start: date, end: date) -> dict[str, dict]:
    """Per-URL GSC aggregates for the window, keyed by traffic_match_key.

    Aggregated in Python rather than the ORM because two URLs can share a
    match key (http/https, www/apex variants of the same page) and the
    impression-weighted position needs the per-day rows anyway. The
    window's row count is modest: one row per page per day.
    """
    from apps.search_console.models import GscPageStat

    stats = (
        GscPageStat.objects
        .filter(website=website, date__gte=start, date__lte=end)
        .values_list("page", "clicks", "impressions", "position")
    )
    by_key: dict[str, dict] = {}
    weight: dict[str, float] = defaultdict(float)
    for page, clicks, impressions, position in stats:
        key = traffic_match_key(page)
        if not key:
            continue
        agg = by_key.setdefault(key, {"clicks": 0, "impressions": 0, "position": None})
        agg["clicks"] += clicks or 0
        agg["impressions"] += impressions or 0
        if position is not None and impressions:
            weight[key] += position * impressions
    for key, agg in by_key.items():
        if agg["impressions"] and weight.get(key):
            agg["position"] = round(weight[key] / agg["impressions"], 1)
    return by_key


def _ai_visits_by_key(website, start: date, end: date) -> Counter:
    """AI-referred pageview counts per traffic_match_key for the window."""
    from apps.analytics.models import PageEvent

    urls = (
        PageEvent.objects
        .filter(
            website=website,
            event_type="pageview",
            timestamp__date__gte=start,
            timestamp__date__lte=end,
            session__medium="ai",
        )
        .values_list("url", flat=True)[:MAX_AI_PAGEVIEWS]
    )
    counts: Counter = Counter()
    for url in urls:
        key = traffic_match_key(url)
        if key:
            counts[key] += 1
    return counts


def _traffic_summary(website, start: date, end: date) -> dict:
    """Window-scoped session totals + AI share for the header strip."""
    from apps.analytics.models import PageEvent, Session
    from apps.search_console.models import GscDailyTotal

    sessions = Session.objects.filter(
        visitor__website_id=website.id,
        started_at__date__gte=start,
        started_at__date__lte=end,
    )
    total_sessions = sessions.count()
    ai_rows = (
        sessions.filter(medium="ai")
        .values_list("source", flat=True)
    )
    by_source: Counter = Counter(ai_rows)
    ai_sessions = sum(by_source.values())
    providers = [
        {
            "source": source,
            "label": AI_PROVIDER_LABELS.get(source, source.title()),
            "sessions": count,
        }
        for source, count in by_source.most_common()
    ]
    return {
        "gsc_connected": _gsc_integration(website),
        "gsc_has_data": GscDailyTotal.objects.filter(website=website).exists(),
        "pixel_active": PageEvent.objects.filter(website=website).exists(),
        "total_sessions": total_sessions,
        "ai_sessions": ai_sessions,
        "ai_percentage": round(100 * ai_sessions / total_sessions, 1) if total_sessions else 0.0,
        "ai_providers": providers,
    }


def enrich_urls_payload(website, payload: dict, *, start: date, end: date) -> None:
    """Mutate the /urls/ payload: per-row traffic for your-site URLs plus
    a window-scoped traffic_summary. Never raises — the citations page
    must render even if an analytics table is unavailable."""
    try:
        summary = _traffic_summary(website, start, end)
    except Exception:  # pragma: no cover — summary is best-effort
        logger.exception("traffic summary failed for website %s", website.id)
        summary = {
            "gsc_connected": False, "gsc_has_data": False, "pixel_active": False,
            "total_sessions": 0, "ai_sessions": 0, "ai_percentage": 0.0,
            "ai_providers": [],
        }
    payload["traffic_summary"] = summary

    rows = payload.get("urls") or []
    targets = [r for r in rows if r.get("source_class") == "your_site"][:MAX_ENRICHED_ROWS]

    gsc_by_key: dict[str, dict] = {}
    if targets and summary["gsc_connected"] and summary["gsc_has_data"]:
        try:
            gsc_by_key = _gsc_by_key(website, start, end)
        except Exception:  # pragma: no cover
            logger.exception("gsc enrichment failed for website %s", website.id)

    ai_by_key: Counter = Counter()
    if targets and summary["pixel_active"]:
        try:
            ai_by_key = _ai_visits_by_key(website, start, end)
        except Exception:  # pragma: no cover
            logger.exception("ai-visit enrichment failed for website %s", website.id)

    for row in rows:
        row["gsc"] = None
        row["ai_visits"] = None
    for row in targets:
        key = traffic_match_key(row.get("normalized_url") or row.get("url") or "")
        row["gsc"] = gsc_by_key.get(key) if gsc_by_key else None
        row["ai_visits"] = ai_by_key.get(key, 0) if summary["pixel_active"] else None


def enrich_url_detail(website, normalized_url: str, *, start: date, end: date,
                      prev_start: date, prev_end: date, is_target: bool) -> dict | None:
    """The detail page's real-traffic block for one of the user's own
    pages: current-window GSC + AI visits with previous-window deltas.
    Returns None for third-party URLs (their traffic is not ours to show).
    """
    if not is_target:
        return None

    gsc_connected = _gsc_integration(website)
    from apps.analytics.models import PageEvent
    pixel_active = PageEvent.objects.filter(website=website).exists()

    key = traffic_match_key(normalized_url)
    gsc = None
    if gsc_connected and key:
        try:
            current = _gsc_by_key(website, start, end).get(key)
            previous = _gsc_by_key(website, prev_start, prev_end).get(key)
            if current:
                prev_clicks = (previous or {}).get("clicks", 0)
                cur_pos = current.get("position")
                prev_pos = (previous or {}).get("position")
                gsc = {
                    "clicks": current["clicks"],
                    "impressions": current["impressions"],
                    "position": cur_pos,
                    "clicks_delta": current["clicks"] - prev_clicks,
                    # Negative delta = moved up the rankings (improvement).
                    "position_delta": (
                        round(cur_pos - prev_pos, 1)
                        if cur_pos is not None and prev_pos is not None else None
                    ),
                }
        except Exception:  # pragma: no cover
            logger.exception("gsc detail enrichment failed for %s", website.id)

    ai_visits = None
    if pixel_active and key:
        try:
            current_visits = _ai_visits_by_key(website, start, end).get(key, 0)
            previous_visits = _ai_visits_by_key(website, prev_start, prev_end).get(key, 0)
            ai_visits = {
                "value": current_visits,
                "delta": current_visits - previous_visits,
            }
        except Exception:  # pragma: no cover
            logger.exception("ai-visit detail enrichment failed for %s", website.id)

    return {
        "gsc_connected": gsc_connected,
        "pixel_active": pixel_active,
        "gsc": gsc,
        "ai_visits": ai_visits,
    }
