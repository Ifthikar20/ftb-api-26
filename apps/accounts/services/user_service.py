import logging

from apps.accounts.models import User, UserProfile
from core.logging.audit_logger import audit_log

logger = logging.getLogger("apps")


class UserService:
    @staticmethod
    def update_profile(*, user: User, **kwargs) -> User:
        """Update user and profile fields."""
        user_fields = {"full_name", "company_name"}
        profile_fields = {"avatar_url", "timezone", "phone", "bio"}

        for field in user_fields & kwargs.keys():
            setattr(user, field, kwargs[field])
        user.save(update_fields=list(user_fields & kwargs.keys()) or ["updated_at"])

        profile, _ = UserProfile.objects.get_or_create(user=user)
        for field in profile_fields & kwargs.keys():
            setattr(profile, field, kwargs[field])
        profile.save()

        audit_log("user.profile_updated", user=user)
        return user

    @staticmethod
    def delete_account(*, user: User) -> None:
        """GDPR Article 17 — soft delete account and anonymize PII."""
        user.is_active = False
        user.email = f"deleted_{user.id}@deleted.invalid"
        user.full_name = "Deleted User"
        user.company_name = ""
        user.save(update_fields=["is_active", "email", "full_name", "company_name"])
        audit_log("user.account_deleted", metadata={"user_id": str(user.id)})

    @staticmethod
    def export_data(*, user: User) -> dict:
        """GDPR Article 15 — export all user data."""
        from apps.websites.models import Website

        return {
            "profile": {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "company_name": user.company_name,
                "plan": user.plan,
                "created_at": user.created_at.isoformat(),
            },
            "websites": list(
                Website.objects.filter(user=user).values("id", "url", "name", "created_at")
            ),
        }

    @staticmethod
    def mark_onboarding_complete(*, user: User) -> None:
        user.onboarding_complete = True
        user.save(update_fields=["onboarding_complete"])
        audit_log("user.onboarding_complete", user=user)
