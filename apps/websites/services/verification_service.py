from apps.websites.models import Website
from apps.websites.services.pixel_service import PixelService


class VerificationService:
    @staticmethod
    def verify_pixel(*, website: Website) -> dict:
        verified = PixelService.verify(website=website)
        return {"verified": verified, "pixel_key": str(website.pixel_key)}
