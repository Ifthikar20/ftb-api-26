import logging

from apps.websites.models import Website
from core.logging.audit_logger import audit_log

logger = logging.getLogger("apps")

PIXEL_JS_TEMPLATE = """
(function() {{
  var gp = window.GrowthPilot = window.GrowthPilot || {{}};
  gp.pixelKey = '{pixel_key}';
  gp.endpoint = '{endpoint}';

  function track(event, data) {{
    var payload = Object.assign({{
      pixel_key: gp.pixelKey,
      event_type: event,
      url: window.location.href,
      referrer: document.referrer,
      timestamp: new Date().toISOString(),
    }}, data || {{}});

    navigator.sendBeacon(gp.endpoint + 'event/', JSON.stringify(payload));
  }}

  gp.track = track;
  track('pageview');
}})();
"""


class PixelService:
    @staticmethod
    def get_snippet(*, website: Website, endpoint: str = "https://api.growthpilot.io/api/v1/track/") -> str:
        """Return the JavaScript snippet to embed on the tracked site."""
        return PIXEL_JS_TEMPLATE.format(pixel_key=str(website.pixel_key), endpoint=endpoint)

    @staticmethod
    def verify(*, website: Website) -> bool:
        """Check whether the pixel is installed correctly on the website."""
        import requests
        try:
            response = requests.get(website.url, timeout=10)
            if str(website.pixel_key) in response.text:
                from django.utils import timezone
                website.pixel_verified = True
                website.pixel_verified_at = timezone.now()
                website.save(update_fields=["pixel_verified", "pixel_verified_at"])
                audit_log("pixel.verified", metadata={"website_id": str(website.id)})
                return True
        except Exception as e:
            logger.warning(f"Pixel verification failed for {website.url}: {e}")
        return False
