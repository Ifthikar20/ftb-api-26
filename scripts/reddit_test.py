#!/usr/bin/env python3
"""
Reddit API smoke test — no app dependencies, just stdlib + requests.

Walks through:
  1. Token grant (script-type app, password flow).
  2. A keyword search across r/all.
  3. Pretty-prints the first 5 results so you can confirm the
     credentials work before we wire any of this into the product.

Usage
-----
Either pass everything on the command line:

    python scripts/reddit_test.py \\
      --client-id <id> \\
      --client-secret <secret> \\
      --username <reddit_user> \\
      --password <reddit_pw> \\
      --query "credentialing service for clinics"

Or set these env vars and just run with --query:

    REDDIT_CLIENT_ID
    REDDIT_CLIENT_SECRET
    REDDIT_USERNAME
    REDDIT_PASSWORD
    REDDIT_USER_AGENT   (optional; a sensible default is used)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

try:
    import requests
except ImportError:
    sys.stderr.write(
        "requests not installed. Activate your venv and run:\n"
        "    pip install requests\n"
    )
    sys.exit(2)


TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
SEARCH_URL = "https://oauth.reddit.com/search"
DEFAULT_USER_AGENT = "cansee.ai:com.cansee.crawler:v0.1 (by /u/cansee-dev)"


def get_token(
    *, client_id: str, client_secret: str, username: str, password: str, user_agent: str
) -> str:
    auth = requests.auth.HTTPBasicAuth(client_id, client_secret)
    data = {"grant_type": "password", "username": username, "password": password}
    headers = {"User-Agent": user_agent}
    resp = requests.post(TOKEN_URL, auth=auth, data=data, headers=headers, timeout=15)
    if resp.status_code != 200:
        sys.stderr.write(
            f"\n  ✗ Token grant failed ({resp.status_code}):\n    {resp.text}\n\n"
            "  Common causes:\n"
            "    - Wrong client_id / client_secret\n"
            "    - 2FA enabled on the Reddit account (use an app password or disable 2FA)\n"
            "    - App type isn't 'script' (re-create at https://www.reddit.com/prefs/apps)\n"
            "    - User-Agent looks bot-like (Reddit blocks generic UAs)\n"
        )
        sys.exit(1)
    payload = resp.json()
    if "error" in payload:
        sys.stderr.write(f"  ✗ Reddit error: {payload}\n")
        sys.exit(1)
    return payload["access_token"]


def search(
    *, token: str, query: str, user_agent: str, limit: int = 5, sort: str = "relevance"
) -> list[dict[str, Any]]:
    headers = {"Authorization": f"bearer {token}", "User-Agent": user_agent}
    params = {"q": query, "limit": limit, "sort": sort, "type": "link", "raw_json": 1}
    resp = requests.get(SEARCH_URL, headers=headers, params=params, timeout=15)
    if resp.status_code != 200:
        sys.stderr.write(f"  ✗ Search failed ({resp.status_code}): {resp.text}\n")
        sys.exit(1)
    data = resp.json()
    return [c["data"] for c in data.get("data", {}).get("children", [])]


def render(rows: list[dict[str, Any]], query: str) -> None:
    if not rows:
        print(f"  (no results for {query!r})")
        return
    bar = "─" * 64
    print(f"\n  Top {len(rows)} results for {query!r}\n  {bar}")
    for i, r in enumerate(rows, 1):
        title = r.get("title", "").strip()
        subreddit = r.get("subreddit", "")
        author = r.get("author", "[deleted]")
        score = r.get("score", 0)
        n_comments = r.get("num_comments", 0)
        permalink = r.get("permalink", "")
        url = f"https://reddit.com{permalink}" if permalink else r.get("url", "")
        selftext = (r.get("selftext", "") or "").strip().replace("\n", " ")
        if len(selftext) > 220:
            selftext = selftext[:217] + "…"

        print(f"\n  [{i}] r/{subreddit}  ·  ⬆ {score}  ·  💬 {n_comments}  ·  /u/{author}")
        print(f"      {title}")
        if selftext:
            print(f"      └ {selftext}")
        print(f"      {url}")
    print()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--client-id", default=os.environ.get("REDDIT_CLIENT_ID"))
    p.add_argument("--client-secret", default=os.environ.get("REDDIT_CLIENT_SECRET"))
    p.add_argument("--username", default=os.environ.get("REDDIT_USERNAME"))
    p.add_argument("--password", default=os.environ.get("REDDIT_PASSWORD"))
    p.add_argument("--user-agent", default=os.environ.get("REDDIT_USER_AGENT", DEFAULT_USER_AGENT))
    p.add_argument("--query", "-q", required=True, help="What to search for")
    p.add_argument("--limit", "-n", type=int, default=5)
    p.add_argument("--sort", default="relevance", choices=["relevance", "hot", "top", "new", "comments"])
    p.add_argument("--json", action="store_true", help="Dump raw JSON instead of pretty output")
    args = p.parse_args()

    missing = [k for k, v in {
        "--client-id / REDDIT_CLIENT_ID": args.client_id,
        "--client-secret / REDDIT_CLIENT_SECRET": args.client_secret,
        "--username / REDDIT_USERNAME": args.username,
        "--password / REDDIT_PASSWORD": args.password,
    }.items() if not v]
    if missing:
        sys.stderr.write("  Missing credentials:\n    " + "\n    ".join(missing) + "\n")
        return 2

    print("  → Requesting access token…")
    token = get_token(
        client_id=args.client_id, client_secret=args.client_secret,
        username=args.username, password=args.password, user_agent=args.user_agent,
    )
    print(f"  ✓ Got token ({token[:8]}…)\n")

    print(f"  → Searching for {args.query!r} (sort={args.sort}, n={args.limit})")
    rows = search(token=token, query=args.query, user_agent=args.user_agent, limit=args.limit, sort=args.sort)
    print(f"  ✓ {len(rows)} result(s)")

    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        render(rows, args.query)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
