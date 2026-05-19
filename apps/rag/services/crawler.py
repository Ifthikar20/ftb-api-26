"""
Multi-page crawler for the RAG knowledge base.

Builds on ``apps.llm_ranking.services.domain_scanner.scan_domain`` (the
single-page scrape we already trust). The crawler adds:

  - sitemap.xml discovery for the root domain
  - same-domain HTML link extraction from a seed page (depth 1)
  - a configurable page cap so we don't accidentally hammer a site

Output is the same shape as ``scan_domain`` per page so the downstream
ingest pipeline can treat homepage / blog / docs uniformly.
"""
from __future__ import annotations

import logging
import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from apps.llm_ranking.services.domain_scanner import scan_domain

logger = logging.getLogger("apps")

DEFAULT_PAGE_CAP = 12
DEFAULT_DEPTH = 1
SITEMAP_TIMEOUT = 8
LINK_FETCH_TIMEOUT = 6
USER_AGENT = (
    "Mozilla/5.0 (compatible; FetchBotRAG/1.0; "
    "+https://fetchbot.ai/bot)"
)


def crawl_site(
    seed_url: str,
    *,
    page_cap: int = DEFAULT_PAGE_CAP,
    depth: int = DEFAULT_DEPTH,
    include_sitemap: bool = True,
) -> list[dict]:
    """
    Crawl a website starting from ``seed_url`` and return per-page scan
    dicts. The seed itself is always included as the first entry.
    """
    seed = _ensure_scheme(seed_url)
    seed_domain = _normalize_domain(urlparse(seed).netloc)
    if not seed_domain:
        return []

    seen: set[str] = set()
    queue: list[tuple[str, int]] = [(seed, 0)]

    if include_sitemap:
        for url in discover_from_sitemap(seed):
            if _normalize_domain(urlparse(url).netloc) != seed_domain:
                continue
            queue.append((url, 0))

    results: list[dict] = []
    while queue and len(results) < page_cap:
        url, d = queue.pop(0)
        canonical = _canonical(url)
        if canonical in seen:
            continue
        seen.add(canonical)

        scan = scan_domain(url)
        scan["url"] = url
        scan["depth"] = d
        scan["kind"] = _kind_from_url(url)
        results.append(scan)

        if not scan.get("success") or d >= depth:
            continue

        for link in extract_same_domain_links(url, seed_domain):
            if _canonical(link) not in seen:
                queue.append((link, d + 1))

    return results[:page_cap]


def discover_from_sitemap(seed_url: str) -> list[str]:
    """
    Try ``/sitemap.xml`` and ``/sitemap_index.xml`` on the seed's host.

    Returns a list of URLs found in the sitemap. Empty list on any
    failure (not a hard error — the crawler still has the seed page).
    """
    parsed = urlparse(_ensure_scheme(seed_url))
    base = f"{parsed.scheme}://{parsed.netloc}"
    candidates = [f"{base}/sitemap.xml", f"{base}/sitemap_index.xml"]

    from core.validators.safe_http import FetchError, safe_get

    urls: list[str] = []
    for sitemap_url in candidates:
        try:
            resp = safe_get(
                sitemap_url,
                timeout=SITEMAP_TIMEOUT,
                max_bytes=2_000_000,  # sitemaps can be large but bounded
                headers={"User-Agent": USER_AGENT},
                allowed_content_types=(
                    "application/xml", "text/xml", "text/plain",
                ),
            )
        except FetchError as exc:
            logger.debug("Sitemap fetch refused/failed for %s: %s", sitemap_url, exc)
            continue
        if resp.status_code != 200:
            continue
        urls.extend(_parse_sitemap_xml(resp.text))
        if urls:
            break

    return urls


def extract_same_domain_links(page_url: str, expected_domain: str) -> list[str]:
    """Fetch ``page_url`` and return outbound links on the same domain."""
    from core.validators.safe_http import FetchError, safe_get

    try:
        resp = safe_get(
            page_url,
            timeout=LINK_FETCH_TIMEOUT,
            max_bytes=400_000,
            headers={"User-Agent": USER_AGENT},
        )
    except FetchError as exc:
        logger.debug("Link fetch refused/failed for %s: %s", page_url, exc)
        return []
    if resp.status_code != 200:
        return []
    parser = _LinkExtractor(base_url=resp.final_url)
    parser.feed(resp.text)

    links = []
    for link in parser.links:
        domain = _normalize_domain(urlparse(link).netloc)
        if domain == expected_domain and not _is_asset(link):
            links.append(link)

    deduped = []
    seen = set()
    for link in links:
        canon = _canonical(link)
        if canon in seen:
            continue
        seen.add(canon)
        deduped.append(link)
    return deduped[:25]


# ── Helpers ────────────────────────────────────────────────────────────────

class _LinkExtractor(HTMLParser):
    def __init__(self, *, base_url: str):
        super().__init__()
        self.base_url = base_url
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        href = dict(attrs).get("href", "")
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            return
        self.links.append(urljoin(self.base_url, href))


_SITEMAP_LOC_RE = re.compile(r"<loc>\s*([^<]+?)\s*</loc>", re.IGNORECASE)


def _parse_sitemap_xml(xml: str) -> list[str]:
    return [m.group(1).strip() for m in _SITEMAP_LOC_RE.finditer(xml or "")]


def _ensure_scheme(url: str) -> str:
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        return f"https://{url}"
    return url


def _normalize_domain(netloc: str) -> str:
    d = (netloc or "").lower().strip()
    if d.startswith("www."):
        d = d[4:]
    return d


def _canonical(url: str) -> str:
    """Stripped form for dedupe — drops fragment, trailing slash, query order."""
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc.lower()}{p.path.rstrip('/')}".lower()


_ASSET_EXTS = (
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico",
    ".pdf", ".zip", ".mp4", ".mp3", ".css", ".js", ".woff", ".woff2",
)


def _is_asset(url: str) -> bool:
    path = urlparse(url).path.lower()
    return any(path.endswith(ext) for ext in _ASSET_EXTS)


def _kind_from_url(url: str) -> str:
    """Best-effort tag from URL path — fed into KnowledgeSource.kind."""
    path = urlparse(url).path.lower()
    if path in ("", "/", "/home", "/index.html"):
        return "homepage"
    if "/blog" in path or "/post" in path or "/news" in path:
        return "blog"
    if "/docs" in path or "/documentation" in path or "/help" in path:
        return "docs"
    if "/product" in path or "/feature" in path or "/pricing" in path:
        return "product"
    if "/review" in path or "/case-stud" in path or "/customer" in path:
        return "review"
    return "other"
