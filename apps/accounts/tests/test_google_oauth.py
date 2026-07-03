"""Tests for the Google login endpoint (POST /api/v1/auth/google/)."""

from unittest.mock import MagicMock, patch

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.accounts.services import oauth_service
from apps.accounts.tests.factories import UserFactory

REDIRECT_URI = "http://localhost:5173/auth/google/callback"


def _stub_response(payload):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(return_value=payload)
    return resp


def _google_mocks(userinfo):
    token_post = patch.object(
        oauth_service.requests, "post",
        return_value=_stub_response({"access_token": "google-at"}),
    )
    userinfo_get = patch.object(
        oauth_service.requests, "get",
        return_value=_stub_response(userinfo),
    )
    return token_post, userinfo_get


@pytest.mark.django_db
class TestGoogleOAuthView:
    def test_creates_user_and_returns_jwt(self, settings):
        settings.GOOGLE_OAUTH_CLIENT_ID = "cid"
        settings.GOOGLE_OAUTH_CLIENT_SECRET = "secret"
        token_post, userinfo_get = _google_mocks(
            {"email": "new.google.user@test.com", "name": "Google User"}
        )
        with token_post as mock_post, userinfo_get:
            response = APIClient().post(
                "/api/v1/auth/google/",
                {"code": "auth-code", "redirect_uri": REDIRECT_URI},
                format="json",
            )

        assert response.status_code == 200
        payload = response.json()["data"]
        assert payload["access"]
        assert payload["user"]["email"] == "new.google.user@test.com"
        # Refresh cookie is set like password login.
        assert any("refresh" in c.lower() for c in response.cookies.keys())

        user = User.objects.get(email="new.google.user@test.com")
        assert user.is_email_verified is True
        assert not user.has_usable_password()

        # The code exchange used our credentials and the SPA redirect URI.
        data = mock_post.call_args.kwargs["data"]
        assert data["code"] == "auth-code"
        assert data["redirect_uri"] == REDIRECT_URI
        assert data["grant_type"] == "authorization_code"

    def test_logs_in_existing_user(self):
        existing = UserFactory(email="existing.google@test.com")
        token_post, userinfo_get = _google_mocks(
            {"email": "existing.google@test.com", "name": "Existing"}
        )
        with token_post, userinfo_get:
            response = APIClient().post(
                "/api/v1/auth/google/",
                {"code": "auth-code", "redirect_uri": REDIRECT_URI},
                format="json",
            )

        assert response.status_code == 200
        assert response.json()["data"]["user"]["id"] == str(existing.id)
        assert User.objects.filter(email__iexact="existing.google@test.com").count() == 1

    def test_missing_code_returns_400(self):
        response = APIClient().post("/api/v1/auth/google/", {}, format="json")
        assert response.status_code == 400
