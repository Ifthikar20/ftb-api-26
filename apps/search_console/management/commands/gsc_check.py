"""End-to-end diagnostic for the Google Search Console integration.

Walks the whole pipeline in order and reports PASS/FAIL per step with a
concrete fix hint on failure:

  1. Settings and OAuth credentials present
  2. Integration row state for the website (connected, active, property)
  3. Live token refresh against Google's token endpoint
  4. Live property listing (proves the API is enabled and scope granted)
  5. Live Search Analytics query (proves data access)
  6. Optional full sync into the local tables (--sync)

Usage:
  python manage.py gsc_check                      # steps 1 only (no website)
  python manage.py gsc_check --website cansee   # match by domain/name/uuid
  python manage.py gsc_check --website <id> --sync

On the prod host:
  docker compose -f docker/docker-compose.prod.yml exec web \
      python manage.py gsc_check --website cansee --sync
"""

from __future__ import annotations

from datetime import timedelta

import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

SITES_ENDPOINT = "https://www.googleapis.com/webmasters/v3/sites"
QUERY_ENDPOINT = "https://www.googleapis.com/webmasters/v3/sites/{site}/searchAnalytics/query"

HINTS = {
    "no_credentials": "Set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET in the environment (.env.prod on the server).",
    "no_website": "Pass --website with a website uuid, domain, or name substring.",
    "not_connected": "Open the Search Performance page in the app and click Connect with Google.",
    "inactive": "The connection was revoked or refresh failed permanently. Reconnect from the Search Performance page.",
    "no_refresh_token": "Google did not issue a refresh token. Disconnect and reconnect; the consent screen must be completed fully.",
    "no_site_url": "No property selected. Reconnect or pick a property in the Search Performance page.",
    "invalid_grant": "Google rejected the refresh token (revoked, or the user is not in the OAuth test users list while the app is in Testing mode). Reconnect from the app after adding the Google account under Audience > Test users.",
    "api_disabled": "Enable the Google Search Console API: Cloud Console > APIs & Services > Library > Google Search Console API > Enable.",
    "insufficient_scope": "The stored grant lacks webmasters.readonly. Add the scope on the consent screen, then disconnect and reconnect so a new consent is issued.",
    "unauthorized": "Access token rejected. Step 3 should have refreshed it; rerun, and if it persists, reconnect from the app.",
}


class Command(BaseCommand):
    help = "Diagnose the Google Search Console integration end to end."

    def add_arguments(self, parser):
        parser.add_argument(
            "--website",
            default="",
            help="Website uuid, domain, or name substring to test against.",
        )
        parser.add_argument(
            "--sync",
            action="store_true",
            help="Also run a real sync into the local tables (writes data).",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=7,
            help="Window size for the live query test (default 7).",
        )

    # -- output helpers -----------------------------------------------------

    def _ok(self, msg):
        self.stdout.write(self.style.SUCCESS(f"[PASS] {msg}"))

    def _fail(self, msg, hint_key=None, extra=""):
        self.stdout.write(self.style.ERROR(f"[FAIL] {msg}"))
        hint = HINTS.get(hint_key, "")
        if hint:
            self.stdout.write(f"       Fix: {hint}")
        if extra:
            self.stdout.write(f"       Detail: {extra}")

    def _info(self, msg):
        self.stdout.write(f"       {msg}")

    def _skip(self, msg):
        self.stdout.write(self.style.WARNING(f"[SKIP] {msg}"))

    # -- google error classification -----------------------------------------

    @staticmethod
    def _classify_google_error(resp) -> tuple[str, str]:
        """Map a Google error response to (hint_key, detail)."""
        try:
            body = resp.json()
        except ValueError:
            body = {}
        message = str(body.get("error", {}).get("message", "") or resp.text[:300])
        lowered = message.lower()
        if resp.status_code == 401:
            return "unauthorized", message
        if resp.status_code == 403:
            if "has not been used" in lowered or "is disabled" in lowered or "accessnotconfigured" in lowered:
                return "api_disabled", message
            if "insufficient" in lowered or "scope" in lowered:
                return "insufficient_scope", message
            return "insufficient_scope", message
        return "unauthorized", message

    # -- steps -----------------------------------------------------------------

    def handle(self, *args, **options):
        self.stdout.write("Google Search Console integration check")
        self.stdout.write("")

        if not self._step_settings():
            return
        website = self._step_website(options["website"])
        if website is None:
            return
        integration = self._step_integration(website)
        if integration is None:
            return
        if not self._step_refresh(integration):
            return
        site_urls = self._step_list_sites(integration)
        if site_urls is None:
            return
        if not self._step_query(integration, options["days"]):
            return
        if options["sync"]:
            self._step_sync(integration)
        else:
            self._skip("Full sync not run (pass --sync to write real data locally).")

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("All checks passed. The Search Console pipeline is working."))

    def _step_settings(self) -> bool:
        from core.integrations import get_registry

        cfg = get_registry().get("gsc")
        if cfg is None or not cfg.is_configured():
            self._fail("OAuth credentials missing", "no_credentials")
            return False
        self._ok("OAuth credentials configured (client id and secret present)")

        redirect = getattr(settings, "GSC_OAUTH_REDIRECT_URI", "")
        frontend = getattr(settings, "FRONTEND_URL", "")
        self._info(f"redirect uri: {redirect}")
        self._info(f"frontend url: {frontend}")
        if "localhost" in redirect and not settings.DEBUG:
            self.stdout.write(self.style.WARNING(
                "       Warning: GSC_OAUTH_REDIRECT_URI points at localhost on a non-debug settings module."
            ))
        return True

    def _step_website(self, needle: str):
        from apps.websites.models import Website

        if not needle:
            self._skip("No --website given; stopping after settings check.")
            self._info("Pass --website <uuid|domain|name> to test a real connection.")
            return None

        from django.core.exceptions import ValidationError

        qs = Website.objects.filter(is_active=True)
        try:
            website = qs.filter(id=needle).first()
        except (ValueError, ValidationError):
            website = None
        if website is None:
            website = (
                qs.filter(url__icontains=needle).first()
                or qs.filter(name__icontains=needle).first()
            )
        if website is None:
            self._fail(f"No website matching {needle!r}", "no_website")
            return None
        self._ok(f"Website found: {website.name} ({website.url})")
        return website

    def _step_integration(self, website):
        from apps.websites.models import Integration

        integration = Integration.objects.filter(website=website, type="gsc").first()
        if integration is None or not (integration.access_token or integration.refresh_token):
            self._fail("No GSC connection for this website", "not_connected")
            return None
        if not integration.is_active:
            self._fail("Connection exists but is deactivated", "inactive")
            return None
        if not integration.refresh_token:
            self._fail("Connected but no refresh token stored", "no_refresh_token")
            return None
        site_url = (integration.metadata or {}).get("site_url")
        if not site_url:
            self._fail("Connected but no Search Console property selected", "no_site_url")
            return None
        self._ok(f"Integration row healthy (property: {site_url})")
        if integration.last_synced_at:
            self._info(f"last synced: {integration.last_synced_at.isoformat()}")
        else:
            self._info("never synced yet")
        return integration

    def _step_refresh(self, integration) -> bool:
        from apps.search_console.services.oauth_service import refresh_access_token

        try:
            refresh_access_token(integration)
        except requests.RequestException as exc:
            self._fail("Token refresh request failed", "unauthorized", str(exc))
            return False
        integration.refresh_from_db()
        if not integration.is_active:
            self._fail("Google rejected the refresh token (invalid_grant)", "invalid_grant")
            return False
        self._ok("Access token refreshed against Google's token endpoint")
        return True

    def _step_list_sites(self, integration):
        try:
            resp = requests.get(
                SITES_ENDPOINT,
                headers={"Authorization": f"Bearer {integration.access_token}"},
                timeout=15,
            )
        except requests.RequestException as exc:
            self._fail("Could not reach the Search Console API", None, str(exc))
            return None
        if resp.status_code != 200:
            hint, detail = self._classify_google_error(resp)
            self._fail(f"Property listing returned HTTP {resp.status_code}", hint, detail)
            return None

        entries = resp.json().get("siteEntry") or []
        urls = [e.get("siteUrl", "") for e in entries]
        self._ok(f"Search Console API reachable; account has {len(urls)} propert{'y' if len(urls) == 1 else 'ies'}")
        for url in urls[:10]:
            self._info(url)
        selected = (integration.metadata or {}).get("site_url")
        if selected not in urls:
            self._fail(
                f"Selected property {selected!r} is not in the account's property list",
                "no_site_url",
            )
            return None
        return urls

    def _step_query(self, integration, days: int) -> bool:
        from urllib.parse import quote

        site_url = integration.metadata["site_url"]
        end = timezone.now().date() - timedelta(days=3)
        start = end - timedelta(days=days - 1)
        try:
            resp = requests.post(
                QUERY_ENDPOINT.format(site=quote(site_url, safe="")),
                json={
                    "startDate": start.isoformat(),
                    "endDate": end.isoformat(),
                    "dimensions": ["date"],
                    "rowLimit": 25,
                },
                headers={"Authorization": f"Bearer {integration.access_token}"},
                timeout=20,
            )
        except requests.RequestException as exc:
            self._fail("Search Analytics query failed to send", None, str(exc))
            return False
        if resp.status_code != 200:
            hint, detail = self._classify_google_error(resp)
            self._fail(f"Search Analytics query returned HTTP {resp.status_code}", hint, detail)
            return False

        rows = resp.json().get("rows") or []
        total_clicks = sum(int(r.get("clicks") or 0) for r in rows)
        total_impressions = sum(int(r.get("impressions") or 0) for r in rows)
        self._ok(
            f"Search Analytics query OK: {len(rows)} days of data "
            f"({start} to {end}), {total_clicks} clicks, {total_impressions} impressions"
        )
        if not rows:
            self.stdout.write(self.style.WARNING(
                "       Warning: zero rows. Normal for a brand-new property or a site "
                "with no impressions in the window; remember GSC data lags 2-3 days."
            ))
        return True

    def _step_sync(self, integration):
        from apps.search_console.models import GscDailyTotal, GscPageStat, GscQueryStat
        from apps.search_console.services import ingestion_service

        start, end = ingestion_service.compute_sync_window(integration)
        result = ingestion_service.sync_window(integration, start_date=start, end_date=end)
        if result.get("skipped"):
            self._fail(f"Sync skipped: {result['skipped']}")
            return
        website = integration.website
        self._ok(
            f"Sync complete for {start} to {end}: "
            f"{result.get('totals', 0)} daily totals, "
            f"{result.get('queries', 0)} query rows, "
            f"{result.get('pages', 0)} page rows upserted"
        )
        self._info(
            "stored rows now: "
            f"totals={GscDailyTotal.objects.filter(website=website).count()}, "
            f"queries={GscQueryStat.objects.filter(website=website).count()}, "
            f"pages={GscPageStat.objects.filter(website=website).count()}"
        )
