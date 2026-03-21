import logging

from core.logging.audit_logger import audit_log
from core.exceptions import ResourceNotFound, PlanLimitExceeded
from core.validators.url_validator import validate_website_url
from apps.websites.models import Website, WebsiteSettings

logger = logging.getLogger("apps")

# Limits disabled for testing — re-enable for production
# PLAN_WEBSITE_LIMITS = {"starter": 1, "growth": 5, "scale": 50}


class WebsiteService:
    @staticmethod
    def create(*, user, url: str, name: str, industry: str = "", platform_type: str = "custom") -> Website:
        """Add a new website for a user."""
        validated_url = validate_website_url(url)

        # Check if a soft-deleted website with the same URL exists — restore it
        existing = Website.all_objects.filter(user=user, url=validated_url, is_deleted=True).first()
        if existing:
            existing.is_deleted = False
            existing.deleted_at = None
            existing.deleted_by = None
            existing.name = name
            existing.industry = industry or existing.industry
            existing.platform_type = platform_type
            existing.save()
            audit_log("website.restored", user=user, metadata={"website_id": str(existing.id)})
            return existing

        website = Website.objects.create(
            user=user, url=validated_url, name=name, industry=industry,
            platform_type=platform_type,
        )
        WebsiteSettings.objects.create(website=website)
        audit_log("website.created", user=user, metadata={"website_id": str(website.id)})
        return website

    @staticmethod
    def get_for_user(*, user, website_id: str) -> Website:
        """Fetch a website ensuring it belongs to the user."""
        try:
            return Website.objects.get(id=website_id, user=user)
        except Website.DoesNotExist:
            raise ResourceNotFound("Website not found.")

    @staticmethod
    def update(*, website: Website, user, **kwargs) -> Website:
        allowed_fields = {"name", "industry"}
        for field in allowed_fields & kwargs.keys():
            setattr(website, field, kwargs[field])
        website.save()
        audit_log("website.updated", user=user, metadata={"website_id": str(website.id)})
        return website

    @staticmethod
    def delete(*, website: Website, user) -> None:
        website.soft_delete(user=user)
        audit_log("website.deleted", user=user, metadata={"website_id": str(website.id)})

    @staticmethod
    def regenerate_pixel_key(*, website: Website, user) -> Website:
        import uuid
        website.pixel_key = uuid.uuid4()
        website.pixel_verified = False
        website.pixel_verified_at = None
        website.save(update_fields=["pixel_key", "pixel_verified", "pixel_verified_at"])
        audit_log("website.pixel_regenerated", user=user, metadata={"website_id": str(website.id)})
        return website
