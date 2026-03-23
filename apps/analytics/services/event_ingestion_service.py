import hashlib
import logging
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlparse

from django.utils import timezone

from apps.analytics.models import PageEvent, Session, Visitor
from apps.websites.models import Website
from core.utils.ua_parser import get_client_ip, parse_user_agent

logger = logging.getLogger("apps")

SESSION_TIMEOUT_MINUTES = 30


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

        ua_info = parse_user_agent(ua_string)

        fingerprint = event_data.get("fingerprint") or event_data.get("visitor_id", "")
        if not fingerprint and ua_string:
            # Generate fingerprint from UA + screen dims + language for anonymous visitors
            fp_parts = f"{ua_string}|{event_data.get('screen_width', '')}|{event_data.get('screen_height', '')}|{event_data.get('language', '')}"
            fingerprint = fp_parts
        fingerprint_hash = hashlib.sha256(fingerprint.encode()).hexdigest()[:64]

        # Detect country from IP using free API (cached per IP)
        geo_country = event_data.get("geo_country", "")
        if not geo_country and client_ip:
            geo_country = EventIngestionService._detect_country(client_ip)

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

    # ── Country detection from IP ──
    _country_cache = {}

    @staticmethod
    def _detect_country(ip: str) -> str:
        """Detect country code from IP using free ip-api.com (non-commercial)."""
        if ip in EventIngestionService._country_cache:
            return EventIngestionService._country_cache[ip]

        # Skip private/local IPs
        if ip.startswith(("127.", "10.", "192.168.", "172.", "::1", "0.")):
            return ""

        try:
            import json as _json
            import urllib.request
            resp = urllib.request.urlopen(
                f"http://ip-api.com/json/{ip}?fields=countryCode", timeout=3
            )
            data = _json.loads(resp.read())
            country = data.get("countryCode", "")
            EventIngestionService._country_cache[ip] = country
            return country
        except Exception:
            return ""

