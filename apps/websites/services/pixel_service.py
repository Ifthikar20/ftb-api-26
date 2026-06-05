import logging

from apps.websites.models import Website
from core.logging.audit_logger import audit_log

logger = logging.getLogger("apps")

# Single source of truth for the user-facing install snippet. Customers paste
# this verbatim into their site's <head>. Versioned via the URL — bump to
# /p2.js etc. if a future pixel needs an incompatible schema.
PIXEL_SCRIPT_URL = "https://fetchbot.ai/p.js"
PIXEL_SNIPPET_TEMPLATE = '<script src="{src}" data-key="{pixel_key}"></script>'


class PixelService:
    @staticmethod
    def get_snippet(*, website: Website, src: str = PIXEL_SCRIPT_URL) -> str:
        """Return the user-visible <script> tag to embed on the tracked site.

        The actual tracking JS lives at PIXEL_SCRIPT_URL and is served by
        nginx; this just produces the one-line snippet a customer pastes
        into their <head>.
        """
        return PIXEL_SNIPPET_TEMPLATE.format(src=src, pixel_key=str(website.pixel_key))

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
                audit_log("pixel.verified", action="update", resource_type="website", resource_id=str(website.id), metadata={"url": website.url})
                return True
        except Exception as e:
            logger.warning(f"Pixel verification failed for {website.url}: {e}")
        return False
