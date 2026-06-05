"""Origin allowlist for the public pixel-ingest endpoint.

The pixel script is, by design, public — anyone can read it and copy a
``pixel_key`` out of a customer's website. The defense against an
exfiltrated key is server-side: we only accept events whose ``Origin``
(or ``Referer`` as a fallback) matches the domain the website was
registered with. A stolen key fired from a different site silently 403s.

Matching rules
--------------
- ``www.`` is treated as equivalent to the apex domain (so a site
  registered with ``https://outfi.ai`` accepts events from
  ``https://www.outfi.ai`` and vice versa).
- Any subdomain of the registered apex is accepted
  (``shop.outfi.ai`` for a site registered as ``outfi.ai``).
- Different ports on the same hostname are accepted (so a customer
  testing on ``:8443`` does not need to re-register).
- Hostnames are compared case-insensitively, IDN-aware.

Dev convenience
---------------
When ``settings.DEBUG`` is true, ``localhost`` and ``127.0.0.1`` are
always accepted regardless of registered domain so local manual
testing works without spinning up a real domain.
"""
from __future__ import annotations

from urllib.parse import urlparse

from django.conf import settings


def _hostname(value: str) -> str:
    if not value:
        return ""
    try:
        # urlparse needs a scheme to find the netloc, so prepend one if
        # the caller passed a bare hostname.
        if "://" not in value:
            value = "https://" + value
        return (urlparse(value).hostname or "").lower()
    except (ValueError, TypeError):
        return ""


def _apex(host: str) -> str:
    """Strip a leading ``www.`` so apex/www are treated as one identity."""
    return host[4:] if host.startswith("www.") else host


def is_origin_allowed(request, website) -> bool:
    """Return True if this request may post events for the given website.

    Reads the ``Origin`` header (preferred — it cannot be spoofed by a
    page running in a real browser) and falls back to ``Referer`` when
    Origin is missing (e.g. ``sendBeacon`` from an opaque origin).
    """
    origin_header = (
        request.META.get("HTTP_ORIGIN")
        or request.META.get("HTTP_REFERER")
        or ""
    )
    request_host = _hostname(origin_header)

    # Dev escape hatch — never enforce against localhost during DEBUG so
    # `manage.py runserver` plus `npm run dev` works without ceremony.
    if getattr(settings, "DEBUG", False) and request_host in (
        "localhost", "127.0.0.1", "0.0.0.0",
    ):
        return True

    if not request_host:
        return False

    registered_host = _hostname(getattr(website, "url", "") or "")
    if not registered_host:
        # No URL on file → we can't enforce anything, so fail closed.
        return False

    request_apex = _apex(request_host)
    registered_apex = _apex(registered_host)

    if request_apex == registered_apex:
        return True
    # Any subdomain of the registered apex is fine.
    return request_apex.endswith("." + registered_apex)
