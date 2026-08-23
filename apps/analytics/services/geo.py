"""Country resolution for incoming pixel events.

Country is resolved through a layered strategy, cheapest and most reliable
first. Each layer is independent — you only need one of them wired up for
country capture to work, and the resolver degrades gracefully if none are.

    1. Trusted edge header. If a CDN or the nginx GeoIP module already
       resolved the country and forwarded it (Cloudflare sets
       ``CF-IPCountry``; an nginx ``geoip2`` block can set
       ``X-Geo-Country``), we trust it directly. Zero latency, zero
       external calls, no database to ship. This is the recommended path
       in production.

    2. Local MaxMind GeoLite2 database. If ``settings.GEOIP_PATH`` points
       at a ``GeoLite2-Country.mmdb`` and the ``geoip2`` package is
       installed, we look the IP up in-process. Fast, no rate limit.

    3. ip-api.com free endpoint. Last-resort network call, rate-limited
       and best-effort. Cached so a busy IP hits it at most once per TTL.

    4. Client-declared country (``event_data['geo_country']``). Least
       trusted — a browser can claim anything — used only if every server
       side method came up empty.

All inputs are normalised to an uppercase ISO-3166 alpha-2 code, or "".
"""
from __future__ import annotations

import re

from django.conf import settings
from django.core.cache import cache

_ISO2_RE = re.compile(r"^[A-Za-z]{2}$")
_PRIVATE_PREFIXES = ("127.", "10.", "192.168.", "172.", "::1", "0.", "fc", "fd")

_GEO_CACHE_PREFIX = "geoip:"
_GEO_CACHE_TTL = 7 * 24 * 3600
_GEO_TIMEOUT_SECONDS = 1.5

# Header(s) a trusted edge sets after resolving country itself. The first
# non-empty, valid ISO-2 value wins. Override via settings.GEO_COUNTRY_HEADERS.
_DEFAULT_GEO_HEADERS = ("HTTP_CF_IPCOUNTRY", "HTTP_X_GEO_COUNTRY")


def _norm(code) -> str:
    code = (code or "").strip().upper()
    # Cloudflare uses "XX" for unknown / "T1" for Tor — treat as no data.
    if not _ISO2_RE.match(code) or code in ("XX", "T1"):
        return ""
    return code


def _is_private(ip: str) -> bool:
    return not ip or ip.lower().startswith(_PRIVATE_PREFIXES)


def _from_header(request) -> str:
    if request is None:
        return ""
    headers = getattr(settings, "GEO_COUNTRY_HEADERS", _DEFAULT_GEO_HEADERS)
    for h in headers:
        val = _norm(request.META.get(h, ""))
        if val:
            return val
    return ""


def _from_maxmind(ip: str) -> str:
    path = getattr(settings, "GEOIP_PATH", "")
    if not path or _is_private(ip):
        return ""
    try:
        from django.contrib.gis.geoip2 import GeoIP2
        g = GeoIP2()
        return _norm(g.country_code(ip))
    except Exception:
        return ""


def _from_ipapi(ip: str) -> str:
    if _is_private(ip):
        return ""
    cache_key = _GEO_CACHE_PREFIX + ip
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    country = ""
    try:
        import json as _json

        from core.validators.safe_http import safe_get
        # Route through safe_get instead of urllib.urlopen: the SSRF guard
        # validates the host and, unlike urlopen, cannot be steered to a
        # file:// or other non-HTTP scheme. (ip is already a validated public
        # address per _is_private above.)
        resp = safe_get(
            f"http://ip-api.com/json/{ip}?fields=countryCode",
            timeout=_GEO_TIMEOUT_SECONDS,
            allowed_content_types=("application/json",),
        )
        country = _norm(_json.loads(resp.text).get("countryCode", ""))
    except Exception:
        country = ""
    # Cache even empty results so a string of failures for one IP does not
    # re-hit the rate-limited API on every event.
    cache.set(cache_key, country, _GEO_CACHE_TTL)
    return country


def resolve_country(*, request=None, ip: str = "", client_value: str = "") -> str:
    """Return an uppercase ISO-2 country code, or "" if undeterminable."""
    return (
        _from_header(request)
        or _from_maxmind(ip)
        or _from_ipapi(ip)
        or _norm(client_value)
    )
