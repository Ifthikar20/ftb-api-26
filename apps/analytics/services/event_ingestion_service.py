import hashlib
import logging
from datetime import datetime, timezone as dt_timezone

from django.utils import timezone

from apps.analytics.models import Visitor, PageEvent, Session
from apps.websites.models import Website

logger = logging.getLogger("apps")


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

        event = PageEvent.objects.create(
            visitor=visitor,
            website=website,
            url=event_data.get("url", "")[:2000],
            referrer=event_data.get("referrer", "")[:2000],
            event_type=event_data.get("event_type", "pageview"),
            event_name=event_data.get("event_name", ""),
            properties=event_data.get("properties", {}),
            timestamp=timestamp,
            scroll_depth=event_data.get("scroll_depth"),
            time_on_page_ms=event_data.get("time_on_page_ms"),
        )

        return event

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
