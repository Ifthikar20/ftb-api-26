"""
Country attribution for citation URLs.

Heuristic, no external service. Resolves a domain to an ISO-2 country
code in two steps:

  1. ccTLD lookup — ``.in`` -> IN, ``.com.au`` -> AU, etc.
  2. Known-domain fallback — small dictionary of well-known platforms
     whose ``.com`` masks a clear country of origin (g2.com -> US,
     trustpilot.com -> DK).

This is intentionally simple. For real geo-IP (resolving
``platform.example.com`` to its hosting country) we'd need MaxMind
GeoLite2 + DNS resolution, which adds a 70MB binary and a network
hop per citation. The heuristic covers ~80% of common cases at zero
infra cost; we can swap to MaxMind later without touching call sites.
"""
from __future__ import annotations

from collections import Counter
from urllib.parse import urlparse

# ccTLD -> ISO-2 country code. Multi-part ccTLDs (.com.au, .co.uk) are
# handled before single-part ones in the lookup.
_MULTI_TLDS = {
    "com.au": "AU", "net.au": "AU", "org.au": "AU",
    "co.uk": "GB", "org.uk": "GB", "ac.uk": "GB", "gov.uk": "GB",
    "co.in": "IN", "co.nz": "NZ", "co.jp": "JP",
    "com.br": "BR", "com.mx": "MX", "com.sg": "SG",
    "com.tr": "TR", "com.ar": "AR",
}

_SINGLE_TLDS = {
    "us": "US", "ca": "CA", "uk": "GB", "in": "IN", "au": "AU",
    "de": "DE", "fr": "FR", "es": "ES", "it": "IT", "nl": "NL",
    "se": "SE", "no": "NO", "dk": "DK", "fi": "FI", "pl": "PL",
    "br": "BR", "mx": "MX", "ar": "AR", "jp": "JP", "kr": "KR",
    "cn": "CN", "ru": "RU", "tr": "TR", "il": "IL", "ae": "AE",
    "sa": "SA", "za": "ZA", "ie": "IE", "pt": "PT", "ch": "CH",
    "be": "BE", "at": "AT", "nz": "NZ", "sg": "SG", "my": "MY",
    "id": "ID", "th": "TH", "vn": "VN", "ph": "PH",
}

# Well-known global domains where the ``.com`` masks a clear origin.
# Keep this short — every entry is a manual judgement call.
_KNOWN_DOMAINS = {
    # SaaS review sites / directories
    "g2.com": "US", "capterra.com": "US", "softwareadvice.com": "US",
    "getapp.com": "US", "trustradius.com": "US", "producthunt.com": "US",
    "trustpilot.com": "DK",
    # Tech publications
    "techcrunch.com": "US", "theverge.com": "US", "wired.com": "US",
    "venturebeat.com": "US", "forbes.com": "US", "cnet.com": "US",
    "bbc.com": "GB", "bbc.co.uk": "GB", "guardian.co.uk": "GB",
    "thenextweb.com": "NL", "yourstory.com": "IN",
    "economictimes.indiatimes.com": "IN", "livemint.com": "IN",
    # Developer communities
    "github.com": "US", "stackoverflow.com": "US", "medium.com": "US",
    "dev.to": "US", "reddit.com": "US", "ycombinator.com": "US",
    # Generic
    "wikipedia.org": "US", "linkedin.com": "US",
}


def attribute_country(url: str) -> str | None:
    """
    Return the ISO-2 country code for a URL, or ``None`` if unknown.

    Strategy: hostname suffix match. A suffix like ``foo.co.uk``
    resolves to GB even when the URL is ``https://x.foo.co.uk/path``.
    """
    if not url:
        return None
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return None
    if not host:
        return None
    if host.startswith("www."):
        host = host[4:]

    if host in _KNOWN_DOMAINS:
        return _KNOWN_DOMAINS[host]
    # Match longest known domain suffix first (e.g. catch ``bbc.co.uk``
    # before falling through to the ``co.uk`` ccTLD rule).
    for known in _KNOWN_DOMAINS:
        if host.endswith("." + known):
            return _KNOWN_DOMAINS[known]

    parts = host.split(".")
    if len(parts) >= 3:
        candidate = ".".join(parts[-2:])
        if candidate in _MULTI_TLDS:
            return _MULTI_TLDS[candidate]
    if parts:
        tld = parts[-1]
        if tld in _SINGLE_TLDS:
            return _SINGLE_TLDS[tld]
    return None


def aggregate_countries(urls: list[str]) -> dict[str, int]:
    """Count citations per country code; URLs with no match are skipped."""
    counter: Counter[str] = Counter()
    for url in urls or []:
        country = attribute_country(url)
        if country:
            counter[country] += 1
    return dict(counter)


def merge_country_counts(*counts: dict[str, int]) -> dict[str, int]:
    """Merge multiple per-result country counts into a per-audit roll-up."""
    total: Counter[str] = Counter()
    for c in counts:
        if c:
            total.update(c)
    return dict(total)
