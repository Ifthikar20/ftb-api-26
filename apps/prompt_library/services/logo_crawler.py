"""Fetch a website's logo given its domain.

Given a bare domain (``tasselsbyrenu.com``) this fetches the homepage and
extracts the best logo it can find, in priority order:

  1. <link rel="apple-touch-icon"> (usually a clean square logo)
  2. <meta property="og:image">    (the brand's share image)
  3. <link rel="icon" / "shortcut icon">
  4. an <img> whose class/id/alt mentions "logo"
  5. /favicon.ico

Results (including misses) are cached so we crawl a domain at most once
per CACHE_TTL. Network failures never raise — the caller gets "" and
falls back to a name lookup / lettered badge.

Safety: the domain is validated and obvious internal/loopback/private
targets are refused to avoid SSRF.
"""
from __future__ import annotations

import ipaddress
import logging
import re
import socket
from urllib.parse import urljoin, urlparse

from django.core.cache import cache

logger = logging.getLogger("apps")

CACHE_TTL = 60 * 60 * 24 * 7      # 7 days — logos rarely change
NEGATIVE_CACHE_TTL = 60 * 60      # retry a miss after an hour
FETCH_TIMEOUT = 5
MAX_BYTES = 600_000               # only need the <head>

_DOMAIN_RE = re.compile(r"^(?=.{1,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$")


def _cache_key(domain: str) -> str:
    return f"site_logo:{domain.lower()}"


def normalise_domain(raw: str) -> str | None:
    """Reduce user input to a bare lowercase host, or None if invalid."""
    if not raw:
        return None
    raw = raw.strip().lower()
    if "//" in raw:
        raw = urlparse(raw).netloc or raw.split("//", 1)[1]
    raw = raw.split("/", 1)[0].split("@")[-1].split(":")[0]
    if raw.startswith("www."):
        raw = raw[4:]
    return raw if _DOMAIN_RE.match(raw) else None


def _is_public_host(domain: str) -> bool:
    """Refuse loopback / private / link-local targets (SSRF guard)."""
    if domain in ("localhost",) or domain.endswith(".local"):
        return False
    try:
        infos = socket.getaddrinfo(domain, None)
    except OSError:
        return False
    for info in infos:
        ip = info[4][0]
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            continue
        if (addr.is_private or addr.is_loopback or addr.is_link_local
                or addr.is_reserved or addr.is_multicast):
            return False
    return True


def fetch_site_logo(domain: str) -> str:
    """Return a logo URL for ``domain`` (cached), or "" if none found."""
    norm = normalise_domain(domain)
    if not norm:
        return ""

    key = _cache_key(norm)
    cached = cache.get(key)
    if cached is not None:
        return cached

    logo = _crawl(norm)
    cache.set(key, logo, CACHE_TTL if logo else NEGATIVE_CACHE_TTL)
    return logo


def _crawl(domain: str) -> str:
    # _is_public_host is only a cheap fast-path: it validates the initial
    # domain but not redirect targets. safe_get re-validates every hop, which
    # is what actually closes the redirect-to-private-IP bypass that the old
    # allow_redirects=True left open.
    if not _is_public_host(domain):
        logger.info("logo crawl refused for non-public host: %s", domain)
        return ""
    from core.validators.safe_http import FetchError, safe_get

    html, final_url = "", f"https://{domain}/"
    for scheme in ("https", "http"):
        url = f"{scheme}://{domain}/"
        try:
            resp = safe_get(
                url, timeout=FETCH_TIMEOUT,
                headers={"User-Agent": "Cansee/1.0 (+https://cansee.ai/bot)"},
            )
            if resp.status_code >= 400:
                continue
            final_url = resp.final_url
            html = resp.text
            break
        except FetchError as exc:
            logger.debug("logo crawl %s failed: %s", url, exc)
            continue

    if html:
        head = html[:MAX_BYTES]
        for candidate in _extract_logo_candidates(head):
            absolute = urljoin(final_url, candidate)
            if absolute.startswith(("http://", "https://")):
                return absolute

    # Last resort: the conventional favicon path (may or may not exist;
    # the browser will 404 -> the UI falls through to its own fallback).
    return f"https://{domain}/favicon.ico"


def _attr(tag: str, name: str) -> str:
    m = re.search(rf'{name}\s*=\s*["\']([^"\']+)["\']', tag, re.I)
    return m.group(1).strip() if m else ""


def _extract_logo_candidates(head: str) -> list[str]:
    """Return candidate logo URLs from the page head, best first."""
    candidates: list[str] = []

    # 1. apple-touch-icon (largest sizes first)
    touch = []
    for tag in re.findall(r"<link\b[^>]*>", head, re.I):
        rel = _attr(tag, "rel").lower()
        if "apple-touch-icon" in rel:
            href = _attr(tag, "href")
            if href:
                sizes = _attr(tag, "sizes")
                px = int(sizes.split("x")[0]) if sizes[:1].isdigit() else 0
                touch.append((px, href))
    candidates += [h for _, h in sorted(touch, key=lambda t: -t[0])]

    # 2. og:image
    for tag in re.findall(r"<meta\b[^>]*>", head, re.I):
        prop = (_attr(tag, "property") or _attr(tag, "name")).lower()
        if prop in ("og:image", "og:image:url", "twitter:image"):
            content = _attr(tag, "content")
            if content:
                candidates.append(content)

    # 3. <link rel="icon" / "shortcut icon">
    for tag in re.findall(r"<link\b[^>]*>", head, re.I):
        rel = _attr(tag, "rel").lower()
        if rel in ("icon", "shortcut icon", "fluid-icon") or "icon" in rel.split():
            href = _attr(tag, "href")
            if href:
                candidates.append(href)

    # 4. <img> whose class/id/alt mentions "logo"
    for tag in re.findall(r"<img\b[^>]*>", head, re.I):
        blob = " ".join([
            _attr(tag, "class"), _attr(tag, "id"), _attr(tag, "alt"),
        ]).lower()
        if "logo" in blob:
            src = _attr(tag, "src") or _attr(tag, "data-src")
            if src:
                candidates.append(src)

    # De-dupe preserving order.
    seen, out = set(), []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out
