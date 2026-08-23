"""URL normalization helpers.

The normalizer canonicalises URLs so that two equivalent links collapse to
the same row in the Citation table. The dedup unique constraint relies on
the ``normalized_url`` column, so this module is the single source of truth
for what "the same URL" means.
"""
from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# Tracking parameters that never affect the document content. Stripped
# during normalization so utm-tagged links collapse onto their canonical
# form.
_TRACKING_PREFIXES = ("utm_",)
_TRACKING_KEYS = {
    "gclid", "fbclid", "ref", "ref_src", "ref_url",
    "mc_cid", "mc_eid", "yclid", "msclkid", "igshid",
    "_hsenc", "_hsmi",
}

# Two-label public suffixes we recognise without tldextract. Far from
# exhaustive, but covers the ones that appear in our miner corpus.
_TWO_LABEL_TLDS = {
    "co.uk", "co.jp", "co.kr", "co.nz", "co.in", "co.za", "co.il",
    "com.au", "com.br", "com.cn", "com.mx", "com.tr", "com.sg", "com.hk",
    "com.tw", "com.ar", "com.pl",
    "ac.uk", "gov.uk", "org.uk",
    "edu.au", "gov.au",
    "ne.jp", "or.jp", "go.jp",
}


def _strip_tracking_params(query: str) -> str:
    if not query:
        return ""
    pairs = []
    for k, v in parse_qsl(query, keep_blank_values=True):
        lk = k.lower()
        if any(lk.startswith(p) for p in _TRACKING_PREFIXES):
            continue
        if lk in _TRACKING_KEYS:
            continue
        pairs.append((k, v))
    return urlencode(pairs)


def _strip_default_port(netloc: str, scheme: str) -> str:
    if scheme == "http" and netloc.endswith(":80"):
        return netloc[:-3]
    if scheme == "https" and netloc.endswith(":443"):
        return netloc[:-4]
    return netloc


def extract_apex_domain(host: str) -> str:
    """Extract the registrable apex (eTLD+1) from a hostname.

    Tries ``tldextract`` if available, otherwise falls back to a small
    set of two-label TLDs. The fallback is good enough for the domains
    that show up in LLM citations; gov.uk / co.uk are the realistic
    failure modes and they're covered.
    """
    if not host:
        return ""
    host = host.lower().strip(".")
    try:  # pragma: no cover - exercised when tldextract is installed
        import tldextract

        ext = tldextract.extract(host)
        if ext.domain and ext.suffix:
            return f"{ext.domain}.{ext.suffix}"
    except Exception:
        pass

    parts = host.split(".")
    if len(parts) <= 2:
        return host
    last_two = ".".join(parts[-2:])
    last_three = ".".join(parts[-3:])
    if last_two in _TWO_LABEL_TLDS and len(parts) >= 3:
        return last_three
    return last_two


def normalize_url(url: str) -> tuple[str, str, str]:
    """Return ``(normalized_url, host, apex_domain)``.

    Lowercases scheme and host, strips fragments, drops tracking params,
    and removes default ports. Idempotent: ``normalize_url(normalize_url(u)[0])``
    yields the same triple.
    """
    if not url:
        return "", "", ""
    url = url.strip()
    parts = urlsplit(url)
    scheme = (parts.scheme or "https").lower()
    # Reject non-http(s) schemes outright. Normalized citation URLs are later
    # rendered as clickable links, so a javascript:/data: scheme reaching here
    # (this is the documented single normalization point) must not survive.
    if scheme not in ("http", "https"):
        return "", "", ""
    netloc = parts.netloc.lower()
    netloc = _strip_default_port(netloc, scheme)
    host = netloc.split("@")[-1].split(":")[0]
    apex = extract_apex_domain(host)
    cleaned_query = _strip_tracking_params(parts.query)
    path = parts.path or ""
    # Strip trailing slash for consistency, except for bare-host URLs.
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")
    normalized = urlunsplit((scheme, netloc, path, cleaned_query, ""))
    return normalized, host, apex
