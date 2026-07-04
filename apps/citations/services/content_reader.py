"""
Type-aware content readers for Source Intelligence scans.

Turns a ranked URL into analyzable text:

- Reddit threads: fetched via Reddit's public JSON API (append .json to
  the permalink), which bypasses the bot-verification wall the HTML
  serves. Comments come back with upvote scores, so the extracted text
  preserves community weighting for the sentiment stage.
- Everything else: fetched through the SSRF-guarded safe_get and
  reduced to visible text with the stdlib HTML parser.

Returned shape (always):
    {"status": "ok"|"blocked"|"error", "kind": "reddit"|"page",
     "text": str, "word_count": int, "detail": str}
"""

from __future__ import annotations

import logging
from html.parser import HTMLParser
from urllib.parse import urlparse

import requests

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
    return read_page(url)
