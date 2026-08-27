"""
Google Analytics 4 API client (Realtime Data API + Admin account listing).

Thin OAuth-bearer client following the conventions of
apps/search_console/services/gsc_client.py: module-level functions,
requests, quota + circuit-breaker guards, narrow exception handling,
never raises — failures are logged and surface as None/[] so callers
fall back to a stale snapshot.

Realtime constraints worth remembering (they shape the snapshot payload):
  - Window is the last 30 minutes only.
  - The dimension set is restricted; source/medium is NOT available,
    so AI-referrer attribution stays a pixel-only feature.
  - Quota is per GA4 property; the DailyQuota below is keyed by website
    so one tenant's open dashboard cannot drain the API budget.
"""

from __future__ import annotations

import logging

import requests
from django.conf import settings
from django.utils import timezone

from core.quota import DailyQuota
from core.resilience.circuit_breaker import CircuitBreaker

logger = logging.getLogger("apps")

DATA_ENDPOINT = "https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runRealtimeReport"
REPORT_ENDPOINT = "https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport"
ACCOUNT_SUMMARIES_ENDPOINT = "https://analyticsadmin.googleapis.com/v1beta/accountSummaries"

DEFAULT_DAILY_LIMIT_PER_WEBSITE = 15000
SNAPSHOT_WINDOW_MINUTES = 30

_breaker = CircuitBreaker(name="ga4", failure_threshold=5, recovery_timeout=120)

_quota = DailyQuota(
    namespace="ga4",
    setting_name="GA4_DAILY_API_LIMIT_PER_WEBSITE",
    default_limit=DEFAULT_DAILY_LIMIT_PER_WEBSITE,
)


def is_configured() -> bool:
    """True when the registry has Google OAuth credentials for ga."""
    from core.integrations import get_registry

    cfg = get_registry().get("ga")
    return bool(cfg and cfg.is_configured())


def _bump(stats: dict | None, key: str) -> None:
    if stats is not None:
        stats[key] = stats.get(key, 0) + 1


def _timeout() -> float:
    return float(getattr(settings, "GA4_FETCH_TIMEOUT_SECONDS", 6.0))


def list_account_summaries(
    access_token: str, *, website_id=None, stats: dict | None = None
) -> list[dict]:
    """
    List the GA4 properties the token can read, via the Admin API.

    Returns [{"property_id": "123456", "display_name": str,
    "account_name": str}, ...]; [] on any failure (logged), open
    breaker, or exhausted quota. A 403 here usually means the Analytics
    Admin API is not enabled on the OAuth client's Google Cloud project.
    """
    if not access_token:
        return []

    properties: list[dict] = []
    page_token = ""
    for _page in range(5):  # accountSummaries pages are 50 accounts each
        if not _breaker.allow():
            _bump(stats, "breaker_blocks")
            return properties
        if not _quota.consume(website_id, 1):
            _bump(stats, "quota_blocks")
            logger.warning("GA4 daily quota exhausted for website %s", website_id)
            return properties
        params = {"pageSize": 50}
        if page_token:
            params["pageToken"] = page_token
        try:
            resp = requests.get(
                ACCOUNT_SUMMARIES_ENDPOINT,
                params=params,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=_timeout(),
            )
            resp.raise_for_status()
            data = resp.json()
            _breaker.record_success()
            _bump(stats, "api_calls")
        except requests.RequestException as exc:
            _breaker.record_failure()
            _bump(stats, "errors")
            logger.warning("GA4 accountSummaries failed: %s", exc)
            return properties
        except ValueError as exc:
            _bump(stats, "errors")
            logger.warning("GA4 accountSummaries returned non-JSON: %s", exc)
            return properties

        for account in data.get("accountSummaries") or []:
            account_name = account.get("displayName", "")
            for prop in account.get("propertySummaries") or []:
                raw = prop.get("property", "")  # "properties/123456"
                property_id = raw.rsplit("/", 1)[-1] if raw else ""
                if property_id:
                    properties.append({
                        "property_id": property_id,
                        "display_name": prop.get("displayName", ""),
                        "account_name": account_name,
                    })

        page_token = data.get("nextPageToken") or ""
        if not page_token:
            break

    return properties


def run_realtime_report(
    access_token: str,
    property_id: str,
    *,
    metrics: list[str],
    dimensions: list[str] | None = None,
    limit: int | None = None,
    order_by_metric: str | None = None,
    dimension_filter: dict | None = None,
    website_id=None,
    stats: dict | None = None,
) -> dict | None:
    """
    Run one Realtime report. Returns Google's raw response dict
    (dimensionHeaders/metricHeaders/rows) or None on open breaker,
    exhausted quota, or any request failure (logged).
    """
    if not access_token or not property_id:
        return None
    if not _breaker.allow():
        _bump(stats, "breaker_blocks")
        return None
    if not _quota.consume(website_id, 1):
        _bump(stats, "quota_blocks")
        logger.warning("GA4 daily quota exhausted for website %s", website_id)
        return None

    body: dict = {"metrics": [{"name": m} for m in metrics]}
    if dimensions:
        body["dimensions"] = [{"name": d} for d in dimensions]
    if limit:
        body["limit"] = int(limit)
    if order_by_metric:
        body["orderBys"] = [{"desc": True, "metric": {"metricName": order_by_metric}}]
    if dimension_filter:
        body["dimensionFilter"] = dimension_filter

    url = DATA_ENDPOINT.format(property_id=property_id)
    try:
        resp = requests.post(
            url,
            json=body,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=_timeout(),
        )
        resp.raise_for_status()
        data = resp.json()
        _breaker.record_success()
        _bump(stats, "api_calls")
    except requests.RequestException as exc:
        _breaker.record_failure()
        _bump(stats, "errors")
        logger.warning("GA4 runRealtimeReport failed for property %s: %s", property_id, exc)
        return None
    except ValueError as exc:
        _bump(stats, "errors")
        logger.warning("GA4 runRealtimeReport returned non-JSON for property %s: %s", property_id, exc)
        return None

    return data


def run_report(
    access_token: str,
    property_id: str,
    *,
    metrics: list[str],
    date_ranges: list[tuple[str, str]],
    dimensions: list[str] | None = None,
    limit: int | None = None,
    order_by_metric: str | None = None,
    website_id=None,
    stats: dict | None = None,
) -> dict | None:
    """
    Run one Core (historical) report. date_ranges are (start, end) ISO
    dates; passing two ranges makes Google add an implicit dateRange
    dimension (values date_range_0/date_range_1) for period deltas.
    Returns the raw response dict or None on open breaker, exhausted
    quota, or any request failure (logged) — same contract as
    run_realtime_report so callers can serve a stale snapshot.
    """
    if not access_token or not property_id or not date_ranges:
        return None
    if not _breaker.allow():
        _bump(stats, "breaker_blocks")
        return None
    if not _quota.consume(website_id, 1):
        _bump(stats, "quota_blocks")
        logger.warning("GA4 daily quota exhausted for website %s", website_id)
        return None

    body: dict = {
        "metrics": [{"name": m} for m in metrics],
        "dateRanges": [{"startDate": start, "endDate": end} for start, end in date_ranges],
    }
    if dimensions:
        body["dimensions"] = [{"name": d} for d in dimensions]
    if limit:
        body["limit"] = int(limit)
    if order_by_metric:
        body["orderBys"] = [{"desc": True, "metric": {"metricName": order_by_metric}}]

    url = REPORT_ENDPOINT.format(property_id=property_id)
    try:
        resp = requests.post(
            url,
            json=body,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=_timeout(),
        )
        resp.raise_for_status()
        data = resp.json()
        _breaker.record_success()
        _bump(stats, "api_calls")
    except requests.RequestException as exc:
        _breaker.record_failure()
        _bump(stats, "errors")
        logger.warning("GA4 runReport failed for property %s: %s", property_id, exc)
        return None
    except ValueError as exc:
        _bump(stats, "errors")
        logger.warning("GA4 runReport returned non-JSON for property %s: %s", property_id, exc)
        return None

    return data


def _rows(report: dict | None) -> list[tuple[list[str], list[float]]]:
    """Flatten a report into (dimension_values, metric_values) tuples."""
    if not report:
        return []
    out = []
    for row in report.get("rows") or []:
        dims = [v.get("value", "") for v in row.get("dimensionValues") or []]
        mets = []
        for v in row.get("metricValues") or []:
            try:
                mets.append(float(v.get("value", 0) or 0))
            except (TypeError, ValueError):
                mets.append(0.0)
        out.append((dims, mets))
    return out


def stream_filter(stream_id: str) -> dict:
    """Realtime dimensionFilter isolating one data stream (hosted-tag pool)."""
    return {
        "filter": {
            "fieldName": "streamId",
            "stringFilter": {"matchType": "EXACT", "value": str(stream_id)},
        }
    }


def build_realtime_snapshot(
    access_token: str,
    property_id: str,
    *,
    website_id=None,
    dimension_filter: dict | None = None,
    source: str = "ga4",
    stats: dict | None = None,
) -> dict | None:
    """
    Compose the realtime snapshot served to the dashboard (4 API calls).

    Returns None when the headline totals call fails, so the caller can
    serve the last cached snapshot instead. Secondary breakdowns degrade
    to empty lists rather than failing the whole snapshot.
    """
    common = {
        "website_id": website_id,
        "dimension_filter": dimension_filter,
        "stats": stats,
    }

    totals = run_realtime_report(
        access_token, property_id, metrics=["activeUsers", "screenPageViews"], **common
    )
    if totals is None:
        return None
    totals_rows = _rows(totals)
    active_users = int(totals_rows[0][1][0]) if totals_rows else 0
    page_views = int(totals_rows[0][1][1]) if totals_rows and len(totals_rows[0][1]) > 1 else 0

    minutes = run_realtime_report(
        access_token,
        property_id,
        metrics=["activeUsers", "screenPageViews"],
        dimensions=["minutesAgo"],
        limit=SNAPSHOT_WINDOW_MINUTES + 1,
        **common,
    )
    by_minute = {}
    for dims, mets in _rows(minutes):
        try:
            by_minute[int(dims[0])] = mets
        except (TypeError, ValueError, IndexError):
            continue
    per_minute = [
        {
            "minutes_ago": m,
            "active_users": int(by_minute.get(m, [0, 0])[0]),
            "page_views": int((by_minute.get(m, [0, 0]) + [0])[1]),
        }
        for m in range(SNAPSHOT_WINDOW_MINUTES - 1, -1, -1)
    ]

    pages = run_realtime_report(
        access_token,
        property_id,
        metrics=["screenPageViews", "activeUsers"],
        dimensions=["unifiedScreenName"],
        limit=10,
        order_by_metric="screenPageViews",
        **common,
    )
    top_pages = [
        {"page": dims[0], "page_views": int(mets[0]), "active_users": int(mets[1]) if len(mets) > 1 else 0}
        for dims, mets in _rows(pages)
        if dims
    ]

    # One country x device call feeds both breakdowns.
    geo = run_realtime_report(
        access_token,
        property_id,
        metrics=["activeUsers"],
        dimensions=["country", "deviceCategory"],
        limit=50,
        **common,
    )
    countries: dict[str, int] = {}
    devices: dict[str, int] = {}
    for dims, mets in _rows(geo):
        if len(dims) < 2 or not mets:
            continue
        value = int(mets[0])
        if dims[0]:
            countries[dims[0]] = countries.get(dims[0], 0) + value
        if dims[1]:
            devices[dims[1]] = devices.get(dims[1], 0) + value

    return {
        "source": source,
        "property_id": property_id,
        "active_users": active_users,
        "page_views": page_views,
        "per_minute": per_minute,
        "top_pages": top_pages,
        "countries": [
            {"country": name, "active_users": count}
            for name, count in sorted(countries.items(), key=lambda kv: -kv[1])[:10]
        ],
        "devices": [
            {"device": name, "active_users": count}
            for name, count in sorted(devices.items(), key=lambda kv: -kv[1])
        ],
        "window_minutes": SNAPSHOT_WINDOW_MINUTES,
        "fetched_at": timezone.now().isoformat(),
    }


__all__ = [
    "build_realtime_snapshot",
    "is_configured",
    "list_account_summaries",
    "run_realtime_report",
    "run_report",
    "stream_filter",
]
