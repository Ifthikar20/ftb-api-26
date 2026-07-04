import logging

import requests
from django.conf import settings

from apps.accounts.models import User
from core.exceptions import PermissionDenied
from core.logging.audit_logger import audit_log

logger = logging.getLogger("apps")

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


class OAuthService:
    @staticmethod
    def google_authenticate(*, code: str, redirect_uri: str) -> User:
        """Exchange Google OAuth code for user info and log in an existing user.

        Public sign-up is closed (accounts are admin-provisioned), so this
        never creates accounts: a Google email without a matching User is
        rejected with a 403.
        """
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

        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            audit_log(
                "user.login_rejected",
                user=None,
                action="login",
                resource_type="user",
                resource_id=email,
                success=False,
                metadata={"method": "google_oauth", "reason": "no_account"},
            )
            raise PermissionDenied(
                "No FetchBot account exists for this Google email. "
                "Contact your administrator for access."
            )

        audit_log("user.login", user=user, action="login", resource_type="user", resource_id=str(user.id), metadata={"method": "google_oauth"})

        return user
