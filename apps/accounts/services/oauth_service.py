import logging

import requests
from django.conf import settings

from apps.accounts.models import User
from core.logging.audit_logger import audit_log

logger = logging.getLogger("apps")

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


class OAuthService:
    @staticmethod
    def google_authenticate(*, code: str, redirect_uri: str) -> User:
        """Exchange Google OAuth code for user info and create/login user."""
        # Exchange code for access token
        token_response = requests.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
                "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=10,
        )
        token_response.raise_for_status()
        tokens = token_response.json()

        # Fetch user info
        userinfo_response = requests.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            timeout=10,
        )
        userinfo_response.raise_for_status()
        userinfo = userinfo_response.json()

        email = userinfo.get("email")
        if not email:
            raise ValueError("Google account did not provide an email address.")

        user, created = User.objects.get_or_create(
            email__iexact=email,
            defaults={
                "email": email,
                "full_name": userinfo.get("name", ""),
                "is_email_verified": True,
            },
        )

        if created:
            user.set_unusable_password()
            user.save()
            audit_log("user.registered", user=user, action="create", resource_type="user", resource_id=str(user.id), metadata={"method": "google_oauth"})
        else:
            audit_log("user.login", user=user, action="login", resource_type="user", resource_id=str(user.id), metadata={"method": "google_oauth"})

        return user
