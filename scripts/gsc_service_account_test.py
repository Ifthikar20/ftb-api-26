#!/usr/bin/env python3
"""Standalone Google Search Console connectivity test using a service
account JSON key. No Django, no OAuth consent screen, no browser.

Use this to prove the Google side works (API enabled, permissions
granted) independently of the app's per-user OAuth flow. Because a
service account never goes through the consent screen, it is immune to
Testing-mode restrictions and app verification status.

One-time Google setup:
  1. Cloud Console > IAM & Admin > Service Accounts > Create service
     account (any name, no roles needed). Open it > Keys > Add key >
     Create new key > JSON. Download the file.
  2. Cloud Console > APIs & Services > Library > enable
     "Google Search Console API".
  3. Search Console (search.google.com/search-console) > your property >
     Settings > Users and permissions > Add user > paste the service
     account email (ends in .iam.gserviceaccount.com), permission
     Full or Restricted.

Usage:
  python scripts/gsc_service_account_test.py --key /path/to/key.json
  python scripts/gsc_service_account_test.py --key key.json --site sc-domain:cansee.ai
  python scripts/gsc_service_account_test.py --key key.json --site sc-domain:cansee.ai --days 28

Requires: google-auth, requests (both already in this project's
requirements via google-generativeai).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta

import requests

SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"
SITES_ENDPOINT = "https://www.googleapis.com/webmasters/v3/sites"
QUERY_ENDPOINT = "https://www.googleapis.com/webmasters/v3/sites/{site}/searchAnalytics/query"

# GSC finalizes data with a 2-3 day lag; never query the newest days.
DATA_LAG_DAYS = 3


def ok(msg):
    print(f"[PASS] {msg}")


def fail(msg, hint=""):
    print(f"[FAIL] {msg}")
    if hint:
        print(f"       Fix: {hint}")
    sys.exit(1)


def info(msg):
    print(f"       {msg}")


def classify(resp) -> str:
    try:
        message = resp.json().get("error", {}).get("message", "")
    except ValueError:
        message = resp.text[:300]
    lowered = message.lower()
    if resp.status_code == 403 and ("has not been used" in lowered or "disabled" in lowered):
        return (
            "Enable the Google Search Console API: Cloud Console > APIs & Services > "
            "Library > Google Search Console API > Enable. Wait a minute, then rerun."
        )
    if resp.status_code == 403:
        return (
            "The service account is not a user on the property. Search Console > "
            "Settings > Users and permissions > Add user with the service account email."
        )
    if resp.status_code == 401:
        return "Token rejected. The key file may be for a deleted service account; create a new key."
    return message


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--key", required=True, help="Path to the service account JSON key file.")
    parser.add_argument("--site", default="", help="Property to query, e.g. sc-domain:cansee.ai or https://cansee.ai/")
    parser.add_argument("--days", type=int, default=7, help="Days of Search Analytics to query (default 7).")
    args = parser.parse_args()

    # Step 1: load the key file.
    try:
        with open(args.key) as fh:
            key_data = json.load(fh)
    except (OSError, ValueError) as exc:
        fail(f"Could not read key file {args.key!r}: {exc}")
    sa_email = key_data.get("client_email", "")
    if key_data.get("type") != "service_account" or not sa_email:
        fail(
            "This JSON is not a service account key.",
            "Cloud Console > IAM & Admin > Service Accounts > (account) > Keys > Add key > JSON. "
            "An OAuth client JSON (starts with 'web' or 'installed') will not work here.",
        )
    ok(f"Key file loaded (service account: {sa_email})")
    info(f"project: {key_data.get('project_id', 'unknown')}")

    # Step 2: exchange the key for an access token.
    try:
        from google.auth.transport.requests import Request
        from google.oauth2 import service_account
    except ImportError:
        fail("google-auth is not installed.", "pip install google-auth")
    try:
        creds = service_account.Credentials.from_service_account_file(args.key, scopes=[SCOPE])
        creds.refresh(Request())
    except Exception as exc:
        fail(f"Token exchange failed: {exc}",
             "The key may be revoked or the system clock skewed. Create a fresh JSON key and retry.")
    ok("Access token obtained from Google")

    headers = {"Authorization": f"Bearer {creds.token}"}

    # Step 3: list properties visible to the service account.
    resp = requests.get(SITES_ENDPOINT, headers=headers, timeout=15)
    if resp.status_code != 200:
        fail(f"Property listing returned HTTP {resp.status_code}", classify(resp))
    entries = resp.json().get("siteEntry") or []
    ok(f"Search Console API reachable; service account can see {len(entries)} propert{'y' if len(entries) == 1 else 'ies'}")
    for entry in entries:
        info(f"{entry.get('siteUrl')}  ({entry.get('permissionLevel')})")
    if not entries:
        fail(
            "The service account has access to zero properties.",
            f"Search Console > Settings > Users and permissions > Add user: {sa_email}",
        )

    # Step 4: query Search Analytics.
    site = args.site or entries[0]["siteUrl"]
    if not args.site:
        info(f"no --site given; using {site}")
    end = date.today() - timedelta(days=DATA_LAG_DAYS)
    start = end - timedelta(days=args.days - 1)
    from urllib.parse import quote

    resp = requests.post(
        QUERY_ENDPOINT.format(site=quote(site, safe="")),
        json={"startDate": start.isoformat(), "endDate": end.isoformat(),
              "dimensions": ["query"], "rowLimit": 10},
        headers=headers,
        timeout=20,
    )
    if resp.status_code != 200:
        fail(f"Search Analytics query returned HTTP {resp.status_code}", classify(resp))
    rows = resp.json().get("rows") or []
    ok(f"Search Analytics query OK for {site} ({start} to {end})")
    if rows:
        info("top queries:")
        for row in rows:
            info(
                f"  {row['keys'][0]!r}: {int(row.get('clicks', 0))} clicks, "
                f"{int(row.get('impressions', 0))} impressions, "
                f"pos {row.get('position', 0):.1f}"
            )
    else:
        info("zero rows returned. Normal for a new property or a quiet window; "
             "GSC data also lags 2-3 days.")

    print()
    print("All connectivity checks passed. Google Search Console access works.")
    print("Note: the app itself uses per-user OAuth, not this key. This script")
    print("only proves the Google project, API, and property permissions are good.")


if __name__ == "__main__":
    main()
