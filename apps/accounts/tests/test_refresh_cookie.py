"""Attributes of the JWT refresh-token cookie.

The refresh and logout endpoints authenticate from ``refresh_token``
alone (``apps/accounts/api/v1/views.py`` reads ``request.COOKIES``), so
SameSite is the only thing standing between them and cross-site request
forgery. The API itself is not exposed the same way: DRF authenticates
from an ``Authorization: Bearer`` header that browsers never attach
automatically, and ``APIView.as_view()`` is wrapped in ``csrf_exempt``.
This cookie is the exception, which is why it gets its own test.

These are pure-function assertions on ``_refresh_cookie_settings`` — no
database, no cache, no HTTP client — so they run anywhere.
"""
import pytest
from django.test import override_settings

from apps.accounts.api.v1.views import (
    REFRESH_COOKIE_SETTINGS,
    _refresh_cookie_settings,
)


class TestRefreshCookieSameSite:
    """SameSite=None would let any origin drive the cookie endpoints."""

    @override_settings(DEBUG=False)
    def test_production_is_samesite_lax(self):
        assert _refresh_cookie_settings()["samesite"] == "Lax"

    @override_settings(DEBUG=False)
    def test_production_is_never_samesite_none(self):
        # The regression this file exists for. SameSite=None instructs the
        # browser to attach the cookie to cross-site POSTs, which is the
        # precondition for forced logout, refresh churn, and login-CSRF.
        # Flipping it back demands csrf_protect on the cookie-reading
        # views first - see the comment above _refresh_cookie_settings.
        assert _refresh_cookie_settings()["samesite"] != "None"

    @override_settings(DEBUG=True)
    def test_dev_is_also_samesite_lax(self):
        assert _refresh_cookie_settings()["samesite"] == "Lax"


class TestRefreshCookieHardening:
    """The flags that keep the cookie unreadable and off plaintext links."""

    @override_settings(DEBUG=False)
    def test_production_cookie_is_secure_and_httponly(self):
        cookie = _refresh_cookie_settings()
        # httponly keeps XSS from reading the refresh token; secure keeps
        # it off any plaintext hop.
        assert cookie["httponly"] is True
        assert cookie["secure"] is True

    @override_settings(DEBUG=True)
    def test_dev_relaxes_secure_but_not_httponly(self):
        # Vite proxies over http locally, so Secure would drop the cookie
        # and bounce developers to /login. httponly is not negotiable.
        cookie = _refresh_cookie_settings()
        assert cookie["secure"] is False
        assert cookie["httponly"] is True

    @pytest.mark.parametrize("debug", [True, False])
    def test_name_path_and_lifetime_match_the_client(self, debug):
        # ftb-ui posts to /api/v1/auth/refresh/ with an empty body and
        # withCredentials, so the cookie must be readable across the whole
        # path. The 7-day max_age matches SIMPLE_JWT REFRESH_TOKEN_LIFETIME.
        with override_settings(DEBUG=debug):
            cookie = _refresh_cookie_settings()
        assert cookie["key"] == "refresh_token"
        assert cookie["path"] == "/"
        assert cookie["max_age"] == 7 * 24 * 60 * 60


class TestModuleLevelConstant:
    """REFRESH_COOKIE_SETTINGS is bound at import, not per request."""

    def test_constant_is_evaluated_once_at_import(self):
        # Every set_cookie call site passes **REFRESH_COOKIE_SETTINGS
        # rather than calling the function, so the value is frozen at
        # import time under whatever DEBUG was then. override_settings
        # cannot reach it - a fact worth pinning, because it means the
        # deployed behaviour is decided by the settings module in use.
        assert REFRESH_COOKIE_SETTINGS["key"] == "refresh_token"
        assert REFRESH_COOKIE_SETTINGS["samesite"] == "Lax"
        assert REFRESH_COOKIE_SETTINGS["httponly"] is True
