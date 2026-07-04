"""
Type-aware content readers for Source Intelligence scans.

Turns a ranked URL into analyzable text:

- Reddit threads: fetched via Reddit's public JSON API (append .json to
  the permalink), which bypasses the bot-verification wall the HTML
  serves. Comments come back with upvote scores, so the extracted text
  preserves community weighting for the sentiment stage.
- Yelp URLs: read through the official Fusion API when YELP_API_KEY is
  set (Yelp HTML always 403s bots). Business pages become rating,
  review count, and the 3 excerpt reviews the API exposes; search and
  category pages become the ranked business list with ratings, which
  is quantified sentiment on its own.
- Everything else: fetched through the SSRF-guarded safe_get and
  reduced to visible text with the stdlib HTML parser.

Returned shape (always):
    {"status": "ok"|"blocked"|"error", "kind": "reddit"|"yelp"|"page",
     "text": str, "word_count": int, "detail": str}
"""

from __future__ import annotations

import logging
from html.parser import HTMLParser
from urllib.parse import parse_qs, unquote, urlparse

import requests
from django.conf import settings

from core.validators.safe_http import FetchError, safe_get

logger = logging.getLogger("apps")

USER_AGENT = "FetchBot/1.0 (source intelligence; +https://fetchbot.ai)"
MAX_TEXT_CHARS = 20000
MAX_REDDIT_COMMENTS = 40
PAGE_TIMEOUT = 12.0


def _result(status: str, kind: str, text: str = "", detail: str = "") -> dict:
    return {
        "status": status,
        "kind": kind,
        "text": text[:MAX_TEXT_CHARS],
        "word_count": len(text.split()),
        "detail": detail[:300],
    }


# -- Reddit -------------------------------------------------------------------

def _is_reddit_thread(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host.endswith("reddit.com") and "/comments/" in url


def _flatten_comments(children: list, out: list) -> None:
    for child in children:
        data = child.get("data") or {}
        if child.get("kind") != "t1":
            continue
        body = (data.get("body") or "").strip()
        if body and body not in ("[deleted]", "[removed]"):
            out.append({"text": body, "score": int(data.get("score") or 0)})
        replies = data.get("replies")
        if isinstance(replies, dict):
            _flatten_comments((replies.get("data") or {}).get("children") or [], out)


def read_reddit_thread(url: str) -> dict:
    """Fetch a Reddit thread via the public JSON API, preserving upvotes."""
    json_url = url.split("?")[0].rstrip("/") + ".json"
    try:
        resp = requests.get(
            json_url,
            headers={"User-Agent": USER_AGENT},
            timeout=PAGE_TIMEOUT,
        )
        resp.raise_for_status()
        payload = resp.json()
    except requests.RequestException as exc:
        return _result("blocked", "reddit", detail=str(exc))
    except ValueError as exc:
        return _result("error", "reddit", detail=f"non-JSON: {exc}")

    try:
        post = payload[0]["data"]["children"][0]["data"]
        comment_children = payload[1]["data"]["children"]
    except (IndexError, KeyError, TypeError) as exc:
        return _result("error", "reddit", detail=f"unexpected shape: {exc}")

    comments: list[dict] = []
    _flatten_comments(comment_children, comments)
    comments.sort(key=lambda c: c["score"], reverse=True)
    comments = comments[:MAX_REDDIT_COMMENTS]

    lines = [
        f"REDDIT THREAD: {post.get('title', '')}",
        f"Subreddit: r/{post.get('subreddit', '')}  Post score: {post.get('score', 0)}",
    ]
    selftext = (post.get("selftext") or "").strip()
    if selftext:
        lines.append(f"Post body: {selftext[:2000]}")
    lines.append("Comments (sorted by upvotes; score = community agreement):")
    for comment in comments:
        lines.append(f"[+{comment['score']}] {comment['text'][:1500]}")

    return _result("ok", "reddit", "\n".join(lines))


# -- Yelp (official Fusion API) ------------------------------------------------

YELP_API_BASE = "https://api.yelp.com/v3"
MAX_YELP_BUSINESSES = 10


def _is_yelp(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host.endswith("yelp.com")


def _yelp_headers() -> dict:
    return {"Authorization": f"Bearer {settings.YELP_API_KEY}"}


def _yelp_get(path: str, params: dict | None = None) -> dict | None:
    try:
        resp = requests.get(
            f"{YELP_API_BASE}{path}",
            params=params or {},
            headers=_yelp_headers(),
            timeout=PAGE_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except (requests.RequestException, ValueError) as exc:
        logger.warning("Yelp API call %s failed: %s", path, exc)
        return None


def _yelp_business_lines(biz: dict) -> str:
    categories = ", ".join(
        c.get("title", "") for c in (biz.get("categories") or [])[:3]
    )
    return (
        f"- {biz.get('name', '?')}: {biz.get('rating', '?')} stars from "
        f"{biz.get('review_count', 0)} reviews"
        + (f", price {biz.get('price')}" if biz.get("price") else "")
        + (f" ({categories})" if categories else "")
    )


def read_yelp(url: str) -> dict:
    """Read a Yelp URL through the Fusion API.

    Star ratings and review counts are explicit, quantified sentiment;
    the text block states that so the extraction stage uses them.
    """
    if not getattr(settings, "YELP_API_KEY", ""):
        return _result("blocked", "yelp", detail="YELP_API_KEY not configured")

    parsed = urlparse(url)
    parts = [p for p in parsed.path.split("/") if p]

    # Business page: yelp.com/biz/<alias>
    if parts and parts[0] == "biz" and len(parts) > 1:
        alias = unquote(parts[1])
        biz = _yelp_get(f"/businesses/{alias}")
        if biz is None:
            return _result("error", "yelp", detail="business lookup failed")
        lines = [
            "YELP BUSINESS (official API; star ratings are aggregate customer sentiment):",
            _yelp_business_lines(biz),
        ]
        reviews = _yelp_get(f"/businesses/{alias}/reviews") or {}
        for review in (reviews.get("reviews") or [])[:3]:
            lines.append(
                f"[{review.get('rating', '?')} stars] {(review.get('text') or '').strip()}"
            )
        return _result("ok", "yelp", "\n".join(lines))

    # Search page: yelp.com/search?find_desc=Bagels&find_loc=Dallas, TX
    # Category page: yelp.com/c/<city>/<category>
    term = location = ""
    if parts and parts[0] == "search":
        qs = parse_qs(parsed.query)
        term = (qs.get("find_desc") or [""])[0]
        location = (qs.get("find_loc") or [""])[0]
    elif parts and parts[0] == "c" and len(parts) > 2:
        location = unquote(parts[1]).replace("-", " ")
        term = unquote(parts[2]).replace("-", " ")

    if not (term and location):
        return _result("blocked", "yelp", detail="unrecognized yelp url shape")

    data = _yelp_get(
        "/businesses/search",
        {"term": term, "location": location, "limit": MAX_YELP_BUSINESSES,
         "sort_by": "best_match"},
    )
    if data is None:
        return _result("error", "yelp", detail="business search failed")
    businesses = data.get("businesses") or []
    if not businesses:
        return _result("error", "yelp", detail="no businesses returned")

    lines = [
        f"YELP RANKING for {term!r} in {location!r} (official API; order is "
        "Yelp's relevance ranking, star ratings are aggregate customer sentiment):",
    ]
    lines.extend(_yelp_business_lines(b) for b in businesses)
    return _result("ok", "yelp", "\n".join(lines))


# -- Generic pages ------------------------------------------------------------

class _TextExtractor(HTMLParser):
    _SKIP = {"script", "style", "noscript", "svg", "nav", "footer", "header"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self.chunks: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in self._SKIP and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data):
        if not self._skip_depth:
            stripped = data.strip()
            if stripped:
                self.chunks.append(stripped)


def read_page(url: str) -> dict:
    """Fetch a regular page through the SSRF guard and extract its text."""
    try:
        resp = safe_get(url, timeout=PAGE_TIMEOUT, headers={"User-Agent": USER_AGENT})
    except FetchError as exc:
        status = "blocked" if "403" in str(exc) or "401" in str(exc) else "error"
        return _result(status, "page", detail=str(exc))

    extractor = _TextExtractor()
    try:
        extractor.feed(resp.text)
    except Exception as exc:
        return _result("error", "page", detail=f"parse error: {exc}")
    return _result("ok", "page", "\n".join(extractor.chunks))


def read_url(url: str) -> dict:
    """Dispatch to the right reader for the URL's source type."""
    if _is_reddit_thread(url):
        return read_reddit_thread(url)
    if _is_yelp(url):
        return read_yelp(url)
    return read_page(url)
