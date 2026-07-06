"""
Safe HTTP fetch for the sources service.

Django-free copy of core/validators/safe_http.py (same hardening:
SSRF guard, redirect re-validation, content-type allowlist, body size
cap). Imports the local url_safety copy. Keep in sync with the core
module when the fetch hardening changes.
"""
from __future__ import annotations

import logging
from urllib.parse import urljoin

import requests

from services.sources.url_safety import (
    UnsafeURLError,
    assert_url_safe,
)

logger = logging.getLogger(__name__)

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
) -> SafeResponse:
    """
    Hardened replacement for ``requests.get``.

    Returns a ``SafeResponse``. Raises ``FetchError`` for any failure
    (network, SSRF rejection, body too large, disallowed content type).
    Treat any exception as "do not use this URL".
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
                max_bytes=max_bytes,
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


def _do_request(
    url: str, *, timeout: float, headers: dict | None, max_bytes: int,
) -> requests.Response:
    """One hop. Streams the body and aborts past ``max_bytes``."""
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
