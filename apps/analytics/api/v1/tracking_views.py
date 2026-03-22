"""
Public views for tracked link redirects and email open pixel.

These endpoints are unauthenticated by design — they're called by email clients
and browsers, not by the API user.
"""
import hashlib
import logging

from django.http import HttpResponseRedirect, HttpResponse
from django.views import View

from apps.analytics.models import TrackedLink
from apps.analytics.services.tracking_service import TrackingService

logger = logging.getLogger("apps")

# 1x1 transparent GIF for email open tracking
_TRACKING_PIXEL = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!"
    b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)


class TrackedLinkRedirectView(View):
    """
    Redirect a tracked link and log the click.

    GET /t/<tracking_key>/?tid=<campaign_recipient_tracking_id>
    """

    def get(self, request, tracking_key):
        try:
            link = TrackingService.get_link(tracking_key)
        except TrackedLink.DoesNotExist:
            return HttpResponse("Link not found.", status=404)

        ip = self._get_ip(request)
        ua = request.META.get("HTTP_USER_AGENT", "")[:500]
        referrer = request.META.get("HTTP_REFERER", "")[:2000]
        tracking_id = request.GET.get("tid", "")

        try:
            TrackingService.record_click(
                tracked_link=link,
                ip=ip,
                user_agent=ua,
                referrer=referrer,
                tracking_id=tracking_id,
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


class EmailOpenPixelView(View):
    """
    Return a 1x1 tracking pixel and record email open.

    GET /api/v1/track/open/<tracking_id>/
    """

    def get(self, request, tracking_id):
        try:
            from apps.leads.services.campaign_service import CampaignService
            CampaignService.record_open(tracking_id=str(tracking_id))
        except Exception as e:
            logger.debug("Open tracking failed for %s: %s", tracking_id, e)

        return HttpResponse(
            _TRACKING_PIXEL,
            content_type="image/gif",
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
        )
