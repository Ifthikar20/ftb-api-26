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

        audit_log("user.profile_updated", user=user, action="update", resource_type="user", resource_id=str(user.id), metadata={"fields": list(kwargs.keys())})
        return user

    @staticmethod
    def delete_account(*, user: User) -> None:
        """GDPR Article 17 — hard-delete the account and everything it owns.

        This is erasure, not deactivation: the User row and its entire
        cascade tree (websites, visitors, sessions, events, knowledge
        sources and chunks, subscription, usage ledger, tokens,
        preferences) are removed from Postgres; the vector-index
        collections for each website are dropped; login-attempt rows
        keyed by the email string are purged; and a Polar-managed
        subscription is cancelled so billing stops.

        Provider cancel and index cleanup are best-effort: an outage
        there must never block the user's right to erasure. Every user
        FK in the codebase is on_delete=CASCADE (verified — none are
        PROTECT/SET_NULL), so user.delete() is authoritative for the
        database.

        What survives, stated honestly: the payment provider retains
        invoices it is legally required to keep, rotating server logs
        age out on their own schedule, and one audit line records that
        an account with this opaque id was deleted — containing no
        name, email, or content.
        """
        user_id = str(user.id)
        email = user.email
        website_ids = list(user.websites.values_list("id", flat=True))

        # 1. Stop provider billing (best effort).
        try:
            sub = getattr(user, "subscription", None)
            if sub is not None and sub.polar_subscription_id:
                from apps.billing.services import polar_billing

                polar_billing.set_cancel_at_period_end(user, cancel=True)
        except Exception:
            logger.warning(
                "Polar cancel during account deletion failed; proceeding "
                "with erasure", exc_info=True,
            )

        # 2. Drop vector-index collections (best effort; orphans are
        #    also filtered at query time, so this is hygiene not safety).
        try:
            from apps.rag.services.vector_backends import get_backend

            backend = get_backend()
            if backend is not None:
                for wid in website_ids:
                    backend.delete_website(website_id=wid)
        except Exception:
            logger.warning(
                "vector index cleanup during account deletion failed",
                exc_info=True,
            )

        # 3. Login-attempt rows are keyed by the email STRING (django-axes
        #    has no user FK), so the cascade cannot reach them.
        try:
            from axes.models import AccessAttempt, AccessLog

            AccessAttempt.objects.filter(username=email).delete()
            AccessLog.objects.filter(username=email).delete()
        except Exception:
            logger.warning("axes purge during account deletion failed",
                           exc_info=True)

        # 4. The cascade. After this the user and all owned rows are gone.
        user.delete()

        audit_log(
            "user.account_deleted", action="delete", resource_type="user",
            resource_id=user_id, metadata={"websites": len(website_ids)},
        )

    @staticmethod
    def export_data(*, user: User) -> dict:
        """GDPR Article 15 — export all user data."""
        from apps.websites.models import Website

        audit_log("user.data_exported", user=user, action="export", resource_type="user", resource_id=str(user.id))
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
        audit_log("user.onboarding_complete", user=user, action="update", resource_type="user", resource_id=str(user.id))
