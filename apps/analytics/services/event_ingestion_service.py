import hashlib
import logging
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlparse

from django.db.models import F
from django.utils import timezone

from apps.analytics.models import PageEvent, Session, Visitor
from apps.analytics.services.geo import resolve_country
from apps.websites.models import Website
from core.utils.ua_parser import get_client_ip, is_bot, parse_user_agent

logger = logging.getLogger("apps")

SESSION_TIMEOUT_MINUTES = 30

# Reject timestamps further than these bounds from server-now and fall back
# to the server clock. A client with a wrong clock (or a forged payload)
# would otherwise drop events into the wrong time bucket and corrupt the
# time-series charts.
MAX_TIMESTAMP_FUTURE_SECONDS = 300        # 5 min of clock skew tolerated forward
MAX_TIMESTAMP_PAST_SECONDS = 24 * 3600    # 24 h back (late sendBeacon flushes)


def _clamp_timestamp(raw, now=None):
    """Parse a client timestamp, falling back to now() when absent or absurd."""
    now = now or timezone.now()
    if not raw:
        return now
    try:
        ts = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return now
    if timezone.is_naive(ts):
        ts = timezone.make_aware(ts, timezone.get_current_timezone())
    delta = (ts - now).total_seconds()
    if delta > MAX_TIMESTAMP_FUTURE_SECONDS or delta < -MAX_TIMESTAMP_PAST_SECONDS:
        return now
    return ts


class EventIngestionService:
    @staticmethod
    def ingest_event(*, pixel_key: str, event_data: dict, request=None) -> PageEvent:
        """Process an incoming pixel event and store it."""
        try:
            website = Website.objects.get(pixel_key=pixel_key, is_active=True)
        except Website.DoesNotExist:
            raise ValueError(f"Invalid pixel key: {pixel_key}") from None

        # Parse user-agent server-side for accuracy
        ua_string = ""
        client_ip = ""
        if request:
            ua_string = request.META.get("HTTP_USER_AGENT", "")
            client_ip = get_client_ip(request)
        if not ua_string:
            ua_string = event_data.get("user_agent", "")

        # Drop automated traffic before it touches the database. Bots
        # (search/SEO/AI crawlers, monitors, headless browsers) otherwise
        # count as visitors and inflate every metric. Returning None keeps
        # the endpoint a 202 so we don't hand crawlers a signal to probe.
        if is_bot(ua_string):
            logger.debug("Dropped bot event for %s (ua=%s)", website.id, ua_string[:80])
            return None

        ua_info = parse_user_agent(ua_string)

        # Prefer the client-supplied fingerprint (it carries more entropy:
        # UA, screen, language, timezone offset, CPU cores). Fall back to a
        # server-built one when absent. Adding timezone + viewport + cores
        # reduces collisions between two people on identical hardware.
        fingerprint = event_data.get("fingerprint") or event_data.get("visitor_id", "")
        if not fingerprint:
            fingerprint = "|".join(str(p) for p in [
                ua_string,
                event_data.get("screen_width", ""),
                event_data.get("screen_height", ""),
                event_data.get("viewport_width", ""),
                event_data.get("viewport_height", ""),
                event_data.get("language", ""),
                event_data.get("timezone_offset", ""),
                event_data.get("hardware_concurrency", ""),
            ])
        # Salt with the website id so the same browser on two different
        # customer sites produces two distinct visitors. This both improves
        # per-site uniqueness and makes cross-site correlation impossible.
        salted = f"{website.id}|{fingerprint}"
        fingerprint_hash = hashlib.sha256(salted.encode()).hexdigest()[:64]

        # Resolve country: trusted edge header -> local MaxMind DB ->
        # ip-api fallback -> client-declared. See services/geo.py.
        geo_country = resolve_country(
            request=request,
            ip=client_ip,
            client_value=event_data.get("geo_country", ""),
        )

        visitor, created = Visitor.objects.get_or_create(
            website=website,
            fingerprint_hash=fingerprint_hash,
            defaults={
                "geo_country": geo_country,
                "geo_city": event_data.get("geo_city", ""),
                "device_type": ua_info["device_type"],
                "browser": ua_info["browser"],
                "os": ua_info["os"],
                "ip_hash": hashlib.sha256(client_ip.encode()).hexdigest()[:64] if client_ip else "",
            },
        )

        # Touch last_seen on every event, but DO NOT bump visit_count here —
        # that is incremented once per new session below, not once per event.
        if not created:
            updates = {"last_seen": timezone.now()}
            # Backfill country if it could not be resolved on the first event
            # (e.g. the geo API was rate-limited) but resolves now. Never
            # overwrite a country we already have.
            if geo_country and not visitor.geo_country:
                updates["geo_country"] = geo_country
            Visitor.objects.filter(pk=visitor.pk).update(**updates)

        timestamp = _clamp_timestamp(event_data.get("timestamp"))

        # Session management — find or create session. session_created tells
        # us whether this event opened a new visit so we can count it once.
        session, session_created = EventIngestionService._get_or_create_session(
            visitor=visitor,
            timestamp=timestamp,
            url=event_data.get("url", ""),
            referrer=event_data.get("referrer", ""),
        )

        # A "visit" is a session. Count it once, when the session is born.
        # The visitor row already starts at visit_count=1 for a brand-new
        # visitor (whose first event also creates the first session), so only
        # increment for returning visitors opening a fresh session.
        if session_created and not created:
            Visitor.objects.filter(pk=visitor.pk).update(visit_count=F("visit_count") + 1)

        event = PageEvent.objects.create(
            visitor=visitor,
            website=website,
            session=session,
            url=event_data.get("url", "")[:2000],
            referrer=event_data.get("referrer", "")[:2000],
            event_type=event_data.get("event_type", "pageview"),
            event_name=event_data.get("event_name", ""),
            properties=event_data.get("properties", {}),
            timestamp=timestamp,
            scroll_depth=event_data.get("scroll_depth"),
            time_on_page_ms=event_data.get("time_on_page_ms"),
        )

        event_type = event_data.get("event_type", "pageview")

        # Update session page count and exit page atomically (F() avoids the
        # read-modify-write race when several events from the same visitor
        # land concurrently).
        if session and event_type == "pageview":
            Session.objects.filter(pk=session.pk).update(
                page_count=F("page_count") + 1,
                exit_page=event_data.get("url", "")[:1000],
            )

        # Close the session on either of the pixel's end-of-visit signals.
        # The pixel emits "session_end" (on beforeunload); older payloads and
        # some integrations send "exit". Accept both so avg-session-duration
        # and bounce metrics actually get an end time.
        if event_type in ("session_end", "exit") and session:
            Session.objects.filter(pk=session.pk).update(
                ended_at=timestamp,
                exit_page=event_data.get("url", "")[:1000],
            )

        return event

    @staticmethod
    def _get_or_create_session(*, visitor, timestamp, url, referrer):
        """Find an active session or open a new one (30-min inactivity = new).

        Returns ``(session, created)`` so the caller can count a visit exactly
        once, when a session is born.
        """
        cutoff = timestamp - timedelta(minutes=SESSION_TIMEOUT_MINUTES)

        # An active session is one whose last activity is within the timeout.
        # Anchoring on last_activity (not started_at) means a 25-minute read
        # followed by a click stays one session instead of being cut off at
        # the 30-minute mark measured from the session's start.
        session = (
            Session.objects.filter(
                visitor=visitor,
                last_activity__gte=cutoff,
                ended_at__isnull=True,
            )
            .order_by("-last_activity")
            .first()
        )

        if session:
            # Keep the rolling activity timestamp fresh for the next event.
            Session.objects.filter(pk=session.pk).update(last_activity=timestamp)
            return session, False

        # Parse UTM parameters from URL or referrer
        source, medium, campaign = EventIngestionService._parse_utm(url, referrer)

        session = Session.objects.create(
            visitor=visitor,
            started_at=timestamp,
            last_activity=timestamp,
            page_count=0,
            entry_page=url[:1000] if url else "",
            source=source,
            medium=medium,
            campaign=campaign,
        )
        return session, True

    @staticmethod
    def _parse_utm(url, referrer):
        """Extract source/medium/campaign from URL params or referrer."""
        source = ""
        medium = ""
        campaign = ""

        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)

            source = params.get("utm_source", [""])[0]
            medium = params.get("utm_medium", [""])[0]
            campaign = params.get("utm_campaign", [""])[0]
        except Exception:
            pass

        # If no UTM, infer from referrer
        if not source and referrer:
            try:
                ref_host = urlparse(referrer).hostname or ""

                # ── AI assistant referrers ──
                if "chat.openai.com" in ref_host or "chatgpt.com" in ref_host:
                    source = "chatgpt"
                    medium = "ai"
                elif "claude.ai" in ref_host:
                    source = "claude"
                    medium = "ai"
                elif "gemini.google.com" in ref_host:
                    source = "gemini"
                    medium = "ai"
                elif "perplexity.ai" in ref_host:
                    source = "perplexity"
                    medium = "ai"
                elif "copilot.microsoft.com" in ref_host:
                    source = "copilot"
                    medium = "ai"
                elif "meta.ai" in ref_host:
                    source = "meta-ai"
                    medium = "ai"
                elif "poe.com" in ref_host:
                    source = "poe"
                    medium = "ai"
                elif "you.com" in ref_host:
                    source = "you"
                    medium = "ai"

                # ── Search engines ──
                elif "google" in ref_host:
                    source = "google"
                    medium = "organic"

                # ── Social platforms ──
                elif "facebook" in ref_host or "fb.com" in ref_host:
                    source = "facebook"
                    medium = "social"
                elif "twitter" in ref_host or "t.co" in ref_host:
                    source = "twitter"
                    medium = "social"
                elif "linkedin" in ref_host:
                    source = "linkedin"
                    medium = "social"
                elif "youtube" in ref_host:
                    source = "youtube"
                    medium = "social"

                elif ref_host:
                    source = ref_host
                    medium = "referral"
            except Exception:
                pass

        if not source:
            source = "direct"

        return source[:100], medium[:100], campaign[:200]

    @staticmethod
    def ingest_batch(*, pixel_key: str, events: list, request=None) -> list:
        """Ingest up to 50 events in one request."""
        results = []
        for event_data in events[:50]:
            try:
                event = EventIngestionService.ingest_event(
                    pixel_key=pixel_key, event_data=event_data, request=request
                )
                results.append(event)
            except Exception as e:
                logger.warning(f"Failed to ingest event: {e}")
        return results

