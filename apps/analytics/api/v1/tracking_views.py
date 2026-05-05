"""
Public views for tracked link redirects.

These endpoints are unauthenticated by design — they're called by browsers,
not by the API user. Email-open tracking was retired with the email-campaign
feature; the tracking pixel is no longer served.
"""
import logging

from django.http import HttpResponseRedirect
from django.views import View

from apps.analytics.models import TrackedLink
from apps.analytics.services.tracking_service import TrackingService

logger = logging.getLogger("apps")


class TrackedLinkRedirectView(View):
    """
    Redirect a tracked link and log the click.

    GET /t/<tracking_key>/
    """

    def get(self, request, tracking_key):
        try:
            link = TrackingService.get_link(tracking_key)
        except TrackedLink.DoesNotExist:
            return HttpResponse("Link not found.", status=404)

        ip = self._get_ip(request)
        ua = request.META.get("HTTP_USER_AGENT", "")[:500]
        referrer = request.META.get("HTTP_REFERER", "")[:2000]

        try:
            TrackingService.record_click(
                tracked_link=link,
                ip=ip,
                user_agent=ua,
                referrer=referrer,
            )
        except Exception as e:
            logger.warning("Failed to record click for %s: %s", tracking_key, e)

        return HttpResponseRedirect(link.destination_url)

    @staticmethod
    def _get_ip(request) -> str:
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")
