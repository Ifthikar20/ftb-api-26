#!/usr/bin/env python3
"""Measure a domain's visibility in Perplexity's search index.

For each query, asks the Perplexity Search API for the top results and
records where (if anywhere) the target domain ranks. Summarizes
coverage, average rank, and every URL of the domain that surfaced.
This measures Perplexity's own index and ranking, which is one of the
AI engines FetchBot tracks; it is not Google's ranking.

Usage:
  python scripts/perplexity_visibility_check.py fetchbot.ai \
      "ai visibility tools" "how to rank in chatgpt answers" "geo marketing software"

  python scripts/perplexity_visibility_check.py fetchbot.ai --queries-file queries.txt
  python scripts/perplexity_visibility_check.py fetchbot.ai "ai seo tools" --json

Reads PERPLEXITY_API_KEY from the shell env or the repo .env file.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

# Same-directory import; works when invoked as python scripts/<name>.py.
from serp_brand_analyzer import (
    _env_file_value,
    domain_of,
    fetch_serp_perplexity,
)


def check_query(query: str, target: str, api_key: str, num: int) -> dict:
    results = fetch_serp_perplexity(query, api_key, num)
    hit = next(
        (r for r in results if domain_of(r["url"]) == target
         or domain_of(r["url"]).endswith("." + target)),
        None,
    )
    return {
        "query": query,
        "results_returned": len(results),
        "rank": hit["rank"] if hit else None,
        "matched_url": hit["url"] if hit else None,
        "matched_title": hit["title"] if hit else None,
        "top_result": results[0]["url"] if results else None,
        "top_domain": domain_of(results[0]["url"]) if results else None,
    }


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("domain", help="Target domain to measure, e.g. fetchbot.ai")
    parser.add_argument("queries", nargs="*", help="Queries to test the domain against.")
    parser.add_argument("--queries-file", default="", help="File with one query per line.")
    parser.add_argument("--num", type=int, default=10, help="Results to inspect per query (default 10).")
    parser.add_argument(
        "--api-key",
        default=os.environ.get("PERPLEXITY_API_KEY", "") or _env_file_value("PERPLEXITY_API_KEY"),
    )
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    if not args.api_key:
        sys.exit(
            "[FAIL] PERPLEXITY_API_KEY not found (shell env, repo .env, or --api-key).\n"
            "       Get one at perplexity.ai > Settings > API (key starts with pplx-)."
        )

    queries = list(args.queries)
    if args.queries_file:
        try:
            with open(args.queries_file) as fh:
                queries.extend(line.strip() for line in fh if line.strip())
        except OSError as exc:
            sys.exit(f"[FAIL] Could not read queries file: {exc}")
    if not queries:
        sys.exit("[FAIL] No queries given. Pass them as arguments or via --queries-file.")

    target = args.domain.lower().removeprefix("www.")
    rows = [check_query(query, target, args.api_key, args.num) for query in queries]

    hits = [row for row in rows if row["rank"] is not None]
    coverage = len(hits) / len(rows)
    avg_rank = (sum(row["rank"] for row in hits) / len(hits)) if hits else None
    summary = {
        "domain": target,
        "queries_tested": len(rows),
        "queries_with_presence": len(hits),
        "coverage": round(coverage, 3),
        "average_rank_when_present": round(avg_rank, 2) if avg_rank else None,
        "surfaced_urls": sorted({row["matched_url"] for row in hits}),
    }

    if args.as_json:
        print(json.dumps({"summary": summary, "per_query": rows}, indent=2))
        return

    print(f"Perplexity index visibility for: {target}")
    print("(Perplexity's own index and ranking, not Google's)")
    print()
    for row in rows:
        if row["rank"] is not None:
            status = f"rank #{row['rank']}  {row['matched_url']}"
        elif row["results_returned"] == 0:
            status = "no results returned for this query"
        else:
            status = f"absent from top {row['results_returned']} (top: {row['top_domain']})"
        print(f"  {row['query']!r}: {status}")
    print()
    print(f"Coverage: present in {len(hits)} of {len(rows)} queries ({coverage:.0%})")
    if avg_rank:
        print(f"Average rank when present: {avg_rank:.1f}")
    if summary["surfaced_urls"]:
        print("URLs Perplexity surfaces for this domain:")
        for url in summary["surfaced_urls"]:
            print(f"  {url}")
    else:
        print("No URLs from this domain appeared for any tested query.")
        print("That is the finding: Perplexity's engine does not currently")
        print("surface this domain for these questions.")


if __name__ == "__main__":
    main()
