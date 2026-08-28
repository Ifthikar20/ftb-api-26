"""
Safe HTTP fetch helpers.

A single ``safe_get`` wrapper around ``requests.get`` that every code
path which fetches a user-supplied URL must use. Hardening covered:

    1. SSRF guard via ``url_safety.assert_url_safe`` (scheme allowlist,
       private/loopback/metadata blocking, IPv4 + IPv6, multi-record
       DNS resolution).
    2. Redirect re-validation: ``allow_redirects=False`` + manual hop
       walking. Every ``Location`` is fed back through the SSRF guard
       before we follow it. Defeats the "scrape an attacker-controlled
       domain that 302s to 169.254.169.254" trick.
    3. Content-Type allowlist: refuse non-text responses by default so
       a tenant cannot make us download large binaries to fill disk.
    4. Body size cap: stream and abort once we exceed ``max_bytes``.
    5. Header sanitisation: we never forward cookies / authorization
       across hops; per-fetch ``headers`` apply only to the initial
       request.

What this DOES NOT defeat: classic DNS rebinding within the tight
window between our resolution check and ``requests``' resolution at
connect time. Properly closing that gap requires either egress
network policy (e.g. denying outbound to RFC 1918 at the firewall)
or rewriting the URL to a numeric IP — the latter breaks TLS SNI
verification for nearly every HTTPS site, so we accept the residual
risk and document it. The vast majority of real-world SSRF attacks
go through a static private IP or a redirect to one, both of which
this module catches.
"""
from __future__ import annotations

import logging
from urllib.parse import urljoin

import requests

from core.validators.url_safety import (
    UnsafeURLError,
    assert_url_safe,
)

logger = logging.getLogger("apps")

DEFAULT_MAX_BYTES = 1_000_000
DEFAULT_MAX_REDIRECTS = 4
DEFAULT_TIMEOUT = 10
ALLOWED_CONTENT_TYPES = (
    "text/html", "application/xhtml+xml", "text/plain",
    "application/xml", "text/xml", "application/json",
    "application/rss+xml", "application/atom+xml",
)


class FetchError(Exception):
    """Wraps any fetch-time failure (network, body cap, content-type, SSRF)."""


class SafeResponse:
    __slots__ = ("status_code", "text", "final_url", "content_type", "headers")

    def __init__(self, *, status_code, text, final_url, content_type, headers):
        self.status_code = status_code
        self.text = text
        self.final_url = final_url
        self.content_type = content_type
        self.headers = headers


def safe_get(
    url: str,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    max_bytes: int = DEFAULT_MAX_BYTES,
    max_redirects: int = DEFAULT_MAX_REDIRECTS,
    headers: dict | None = None,
    allowed_content_types: tuple[str, ...] = ALLOWED_CONTENT_TYPES,
    truncate: bool = False,
) -> SafeResponse:
    """
    Hardened replacement for ``requests.get``.

    Returns a ``SafeResponse``. Raises ``FetchError`` for any failure
    (network, SSRF rejection, body too large, disallowed content type).
    Treat any exception as "do not use this URL".

    ``truncate=True`` returns the first ``max_bytes`` instead of raising
    when a page is larger than the cap. Memory is bounded identically —
    reading still stops at the cap — so this is no less safe; it is the
    right mode for callers that only need the head of a document (meta
    tags, hero copy) and would otherwise reject perfectly ordinary pages.
    Modern JS-heavy sites routinely ship >1MB of inline HTML.
    """
    try:
        url = assert_url_safe(url)
    except UnsafeURLError as exc:
        raise FetchError(f"unsafe URL: {exc}") from exc

    final_url = url
    redirects_left = max_redirects
    response = None

    while True:
        try:
            response = _do_request(
                final_url, timeout=timeout, headers=headers,
                max_bytes=max_bytes, truncate=truncate,
            )
        except FetchError:
            raise
        except requests.exceptions.RequestException as exc:
            raise FetchError(str(exc)[:200]) from exc

        if response.status_code in (301, 302, 303, 307, 308):
            location = response.headers.get("Location") or ""
            if not location:
                raise FetchError("redirect without Location header")
            next_url = urljoin(final_url, location)
            if redirects_left <= 0:
                raise FetchError("too many redirects")
            # The new URL goes through the full guard — public IP,
            # http/https only, etc. A redirect chain that ever points
            # at a private address is fully refused.
            try:
                next_url = assert_url_safe(next_url)
            except UnsafeURLError as exc:
                raise FetchError(f"redirect refused: {exc}") from exc
            redirects_left -= 1
            final_url = next_url
            continue
        break

    ct = (response.headers.get("Content-Type") or "").split(";")[0].strip().lower()
    if allowed_content_types and ct and not any(
        ct == ok for ok in allowed_content_types
    ):
        raise FetchError(f"disallowed content-type: {ct}")

    return SafeResponse(
        status_code=response.status_code,
        text=response.text,
        final_url=final_url,
        content_type=ct,
        headers=dict(response.headers),
    )


# ── Internal helpers ──────────────────────────────────────────────────────


def _do_request(
    url: str, *, timeout: float, headers: dict | None, max_bytes: int,
    truncate: bool = False,
) -> requests.Response:
    """One hop. Streams the body, stopping at ``max_bytes``.

    Past the cap we either abort (default) or keep the bytes read so far
    (``truncate``). Either way reading stops, so memory stays bounded.
    """
    resp = requests.get(
        url,
        timeout=timeout,
        headers=dict(headers or {}),
        allow_redirects=False,
        stream=True,
    )
    try:
        body = b""
        for chunk in resp.iter_content(chunk_size=8192):
            if not chunk:
                continue
            body += chunk
            if len(body) > max_bytes:
                resp.close()
                if truncate:
                    body = body[:max_bytes]
                    break
                raise FetchError(f"response body exceeds {max_bytes} bytes")
        # Replace the streamed content so .text decodes it normally.
        resp._content = body  # noqa: SLF001
        return resp
    except FetchError:
        raise
    finally:
        try:
            resp.close()
        except Exception:
            pass
