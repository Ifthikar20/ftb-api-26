#!/usr/bin/env python3
"""SERP brand ranking + on-page SEO analysis for any Google query.

Fetches the top organic Google results for a query via the Custom
Search JSON API (the same GOOGLE_API_KEY / GOOGLE_CSE_ID this project
already uses), identifies the brand behind each result, then fetches
each page and scores basic on-page SEO signals.

Note this is intentionally NOT the Search Console API: Search Console
only reports your own verified property's performance. Seeing who
ranks for an arbitrary query requires a search API.

Usage:
  export GOOGLE_API_KEY=...        # or pass --api-key
  export GOOGLE_CSE_ID=...         # or pass --cse-id
  python scripts/serp_brand_analyzer.py "best bagels in dallas"
  python scripts/serp_brand_analyzer.py "best bagels in dallas" --num 10 --no-fetch
  python scripts/serp_brand_analyzer.py "best crm software" --json

Output: ranked table of brands/domains with per-page SEO measurements
(title, meta description, H1, word count, schema.org, Open Graph),
plus a summary of which brands dominate the SERP.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from html.parser import HTMLParser
from urllib.parse import urlparse

import requests

CSE_ENDPOINT = "https://www.googleapis.com/customsearch/v1"
PAGE_TIMEOUT = 10.0
USER_AGENT = "Mozilla/5.0 (compatible; FetchBot-SEO-Analyzer/1.0)"

# Reasonable on-page targets used for the PASS/WARN annotations.
TITLE_MAX = 60
META_DESC_MIN, META_DESC_MAX = 70, 160
THIN_CONTENT_WORDS = 300


# ── SERP fetch ────────────────────────────────────────────────────────────

def fetch_serp(query: str, api_key: str, cse_id: str, num: int) -> list[dict]:
    resp = requests.get(
        CSE_ENDPOINT,
        params={"key": api_key, "cx": cse_id, "q": query, "num": min(num, 10)},
        timeout=15,
    )
    if resp.status_code != 200:
        try:
            message = resp.json().get("error", {}).get("message", resp.text[:200])
        except ValueError:
            message = resp.text[:200]
        sys.exit(f"[FAIL] Custom Search API returned HTTP {resp.status_code}: {message}")
    items = resp.json().get("items") or []
    return [
        {
            "rank": idx,
            "url": item.get("link", ""),
            "title": item.get("title", ""),
            "snippet": item.get("snippet", ""),
        }
        for idx, item in enumerate(items, start=1)
    ]


# ── On-page SEO extraction ─────────────────────────────────────────────────

class SEOPageParser(HTMLParser):
    """Pull the SEO-relevant bits out of an HTML page with the stdlib
    parser (same approach as apps/llm_ranking/services/domain_scanner.py)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.meta_description = ""
        self.og_site_name = ""
        self.og_title = ""
        self.h1s: list[str] = []
        self.has_json_ld = False
        self.json_ld_types: list[str] = []
        self.canonical = ""
        self.word_count = 0
        self._in_title = False
        self._in_h1 = False
        self._in_script = False
        self._in_style = False
        self._json_ld_buffer = ""
        self._capturing_json_ld = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "h1":
            self._in_h1 = True
            self.h1s.append("")
        elif tag == "meta":
            name = (attrs.get("name") or "").lower()
            prop = (attrs.get("property") or "").lower()
            content = attrs.get("content") or ""
            if name == "description" and not self.meta_description:
                self.meta_description = content.strip()
            elif prop == "og:site_name":
                self.og_site_name = content.strip()
            elif prop == "og:title":
                self.og_title = content.strip()
        elif tag == "link" and (attrs.get("rel") or "").lower() == "canonical":
            self.canonical = attrs.get("href") or ""
        elif tag == "script":
            self._in_script = True
            if (attrs.get("type") or "").lower() == "application/ld+json":
                self.has_json_ld = True
                self._capturing_json_ld = True
                self._json_ld_buffer = ""
        elif tag == "style":
            self._in_style = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "h1":
            self._in_h1 = False
        elif tag == "script":
            self._in_script = False
            if self._capturing_json_ld:
                self._capturing_json_ld = False
                try:
                    data = json.loads(self._json_ld_buffer)
                except ValueError:
                    return
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if isinstance(item, dict) and item.get("@type"):
                        type_value = item["@type"]
                        if isinstance(type_value, list):
                            self.json_ld_types.extend(str(t) for t in type_value)
                        else:
                            self.json_ld_types.append(str(type_value))
        elif tag == "style":
            self._in_style = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._in_h1 and self.h1s:
            self.h1s[-1] += data
        if self._capturing_json_ld:
            self._json_ld_buffer += data
        if not self._in_script and not self._in_style:
            self.word_count += len(data.split())


def analyze_page(url: str) -> dict:
    """Fetch a result URL and extract on-page SEO signals."""
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=PAGE_TIMEOUT,
            allow_redirects=True,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        return {"fetch_error": str(exc)[:120]}

    parser = SEOPageParser()
    try:
        parser.feed(resp.text)
    except Exception as exc:
        return {"fetch_error": f"parse error: {exc}"[:120]}

    return {
        "title": parser.title.strip(),
        "title_length": len(parser.title.strip()),
        "meta_description": parser.meta_description,
        "meta_description_length": len(parser.meta_description),
        "h1": parser.h1s[0].strip() if parser.h1s else "",
        "h1_count": len(parser.h1s),
        "word_count": parser.word_count,
        "has_json_ld": parser.has_json_ld,
        "json_ld_types": parser.json_ld_types[:6],
        "og_site_name": parser.og_site_name,
        "canonical": parser.canonical,
        "https": url.startswith("https://"),
    }


# ── Brand identification ───────────────────────────────────────────────────

def brand_from(url: str, page: dict | None) -> str:
    """Best-effort brand name: og:site_name beats the domain label."""
    if page and page.get("og_site_name"):
        return page["og_site_name"]
    host = urlparse(url).hostname or ""
    host = host[4:] if host.startswith("www.") else host
    label = host.split(".")[0] if host else url
    return label.replace("-", " ").title()


def domain_of(url: str) -> str:
    host = urlparse(url).hostname or ""
    return host[4:] if host.startswith("www.") else host


# ── Reporting ─────────────────────────────────────────────────────────────

def seo_flags(page: dict) -> list[str]:
    flags = []
    if page.get("fetch_error"):
        return [f"unreachable ({page['fetch_error']})"]
    if not page["title"]:
        flags.append("missing <title>")
    elif page["title_length"] > TITLE_MAX:
        flags.append(f"title too long ({page['title_length']} chars)")
    if not page["meta_description"]:
        flags.append("missing meta description")
    elif not (META_DESC_MIN <= page["meta_description_length"] <= META_DESC_MAX):
        flags.append(f"meta description {page['meta_description_length']} chars (target {META_DESC_MIN}-{META_DESC_MAX})")
    if page["h1_count"] == 0:
        flags.append("no H1")
    elif page["h1_count"] > 1:
        flags.append(f"{page['h1_count']} H1 tags")
    if page["word_count"] < THIN_CONTENT_WORDS:
        flags.append(f"thin content ({page['word_count']} words)")
    if not page["has_json_ld"]:
        flags.append("no schema.org JSON-LD")
    if not page["https"]:
        flags.append("not HTTPS")
    return flags


def _env_file_value(*names: str) -> str:
    """Read a value from the repo's .env without sourcing it (the file
    may contain non-shell lines). First matching name wins."""
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    try:
        with open(env_path) as fh:
            lines = fh.readlines()
    except OSError:
        return ""
    values = {}
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    for name in names:
        if values.get(name):
            return values[name]
    return ""


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("query", help='Search query, e.g. "best bagels in dallas"')
    parser.add_argument("--num", type=int, default=10, help="Results to analyze (max 10 per API call).")
    # Precedence: flag > shell env > repo .env (new names, then legacy names).
    parser.add_argument(
        "--api-key",
        default=os.environ.get("GOOGLE_API_KEY", "")
        or _env_file_value("GOOGLE_API_KEY", "GOOGLE_SEARCH_API_KEY"),
    )
    parser.add_argument(
        "--cse-id",
        default=os.environ.get("GOOGLE_CSE_ID", "")
        or _env_file_value("GOOGLE_CSE_ID", "GOOGLE_SEARCH_ENGINE_ID"),
    )
    parser.add_argument("--no-fetch", action="store_true",
                        help="Skip fetching each page (ranking + brands only, no on-page analysis).")
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="Emit machine-readable JSON instead of the report.")
    args = parser.parse_args()

    if not args.api_key or not args.cse_id:
        sys.exit(
            "[FAIL] Missing credentials. Set GOOGLE_API_KEY and GOOGLE_CSE_ID env vars "
            "(the same values from .env) or pass --api-key/--cse-id.\n"
            "       These are Custom Search API credentials, not the OAuth client:\n"
            "       key: Cloud Console > APIs & Services > Credentials > API key\n"
            "       cx:  programmablesearchengine.google.com > your engine > Search engine ID"
        )

    results = fetch_serp(args.query, args.api_key, args.cse_id, args.num)
    if not results:
        sys.exit(f"[FAIL] No results returned for {args.query!r}. "
                 "Check that the search engine is set to search the entire web.")

    for result in results:
        page = None if args.no_fetch else analyze_page(result["url"])
        result["page"] = page
        result["brand"] = brand_from(result["url"], page)
        result["domain"] = domain_of(result["url"])

    # Brand share: how many of the top N each brand/domain owns.
    share: dict[str, dict] = {}
    for result in results:
        entry = share.setdefault(
            result["domain"], {"brand": result["brand"], "count": 0, "best_rank": result["rank"]}
        )
        entry["count"] += 1
        entry["best_rank"] = min(entry["best_rank"], result["rank"])
    leaderboard = sorted(share.items(), key=lambda kv: (kv[1]["best_rank"],))

    if args.as_json:
        print(json.dumps({"query": args.query, "results": results,
                          "brand_share": share}, indent=2))
        return

    print(f'SERP analysis for: "{args.query}"')
    print(f"Top {len(results)} organic Google results (Custom Search API)")
    print()
    print("Brand leaderboard:")
    for domain, entry in leaderboard:
        slots = f", {entry['count']} of top {len(results)}" if entry["count"] > 1 else ""
        print(f"  #{entry['best_rank']}  {entry['brand']}  ({domain}{slots})")
    print()

    for result in results:
        print(f"#{result['rank']}  {result['brand']}  -  {result['url']}")
        print(f"    SERP title: {result['title']}")
        page = result["page"]
        if page is None:
            print("    (page fetch skipped)")
        elif page.get("fetch_error"):
            print(f"    page unreachable: {page['fetch_error']}")
        else:
            print(f"    on-page title ({page['title_length']} chars): {page['title'][:90]}")
            desc = page["meta_description"][:90] or "(none)"
            print(f"    meta description ({page['meta_description_length']} chars): {desc}")
            h1 = page["h1"][:90] or "(none)"
            print(f"    H1: {h1}")
            schema = ", ".join(page["json_ld_types"]) if page["json_ld_types"] else (
                "yes" if page["has_json_ld"] else "no")
            print(f"    words: {page['word_count']}, schema.org: {schema}")
            flags = seo_flags(page)
            if flags:
                print(f"    issues: {'; '.join(flags)}")
            else:
                print("    issues: none, clean on-page SEO")
        print()


if __name__ == "__main__":
    main()
