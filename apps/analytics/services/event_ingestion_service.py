import hashlib
import logging
from datetime import datetime, timedelta, timezone as dt_timezone
from urllib.parse import urlparse, parse_qs

from django.utils import timezone

from apps.analytics.models import Visitor, PageEvent, Session
from apps.websites.models import Website

logger = logging.getLogger("apps")

SESSION_TIMEOUT_MINUTES = 30


class EventIngestionService:
    @staticmethod
    def ingest_event(*, pixel_key: str, event_data: dict) -> PageEvent:
        """Process an incoming pixel event and store it."""
        try:
            website = Website.objects.get(pixel_key=pixel_key, is_active=True)
        except Website.DoesNotExist:
            raise ValueError(f"Invalid pixel key: {pixel_key}")

        fingerprint = event_data.get("fingerprint") or event_data.get("visitor_id", "")
        fingerprint_hash = hashlib.sha256(fingerprint.encode()).hexdigest()[:64]

        visitor, created = Visitor.objects.get_or_create(
            website=website,
            fingerprint_hash=fingerprint_hash,
            defaults={
                "geo_country": event_data.get("geo_country", ""),
                "geo_city": event_data.get("geo_city", ""),
                "device_type": event_data.get("device_type", ""),
                "browser": event_data.get("browser", ""),
                "os": event_data.get("os", ""),
            },
        )

        if not created:
            Visitor.objects.filter(pk=visitor.pk).update(
                visit_count=visitor.visit_count + 1,
                last_seen=timezone.now(),
            )

        timestamp_str = event_data.get("timestamp")
        if timestamp_str:
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                timestamp = timezone.now()
        else:
            timestamp = timezone.now()

        # Session management — find or create session
        session = EventIngestionService._get_or_create_session(
            visitor=visitor,
            timestamp=timestamp,
            url=event_data.get("url", ""),
            referrer=event_data.get("referrer", ""),
        )

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

        # Update session with page count and exit page
        if session and event_data.get("event_type", "pageview") == "pageview":
            Session.objects.filter(pk=session.pk).update(
                page_count=session.page_count + 1,
                exit_page=event_data.get("url", "")[:1000],
            )

        # Update session end time on exit events
        if event_data.get("event_type") == "exit" and session:
            Session.objects.filter(pk=session.pk).update(
                ended_at=timestamp,
                exit_page=event_data.get("url", "")[:1000],
            )

        return event

    @staticmethod
    def _get_or_create_session(*, visitor, timestamp, url, referrer):
        """Find an active session or create a new one. 30-min inactivity = new session."""
        cutoff = timestamp - timedelta(minutes=SESSION_TIMEOUT_MINUTES)

        # Look for a recent session
        session = Session.objects.filter(
            visitor=visitor,
            started_at__gte=cutoff,
            ended_at__isnull=True,
        ).order_by("-started_at").first()

        if session:
            return session

        # Parse UTM parameters from URL or referrer
        source, medium, campaign = EventIngestionService._parse_utm(url, referrer)

        # Create new session
        session = Session.objects.create(
            visitor=visitor,
            started_at=timestamp,
            page_count=0,
            entry_page=url[:1000] if url else "",
            source=source,
            medium=medium,
            campaign=campaign,
        )
        return session

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
                if "google" in ref_host:
                    source = "google"
                    medium = "organic"
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
    def ingest_batch(*, pixel_key: str, events: list) -> list:
        """Ingest up to 50 events in one request."""
        results = []
        for event_data in events[:50]:
            try:
                event = EventIngestionService.ingest_event(
                    pixel_key=pixel_key, event_data=event_data
                )
                results.append(event)
            except Exception as e:
                logger.warning(f"Failed to ingest event: {e}")
        return results
