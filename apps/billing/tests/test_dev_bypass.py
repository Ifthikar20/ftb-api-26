"""
Tests for the dev-only Stripe bypass path in create_checkout_session.

When DEBUG=True AND either STRIPE_SECRET_KEY or the resolved price ID
is missing, the service must:
    - skip the Stripe SDK entirely
    - provision an active Subscription on the requested plan
    - return a success URL with ``session_id=dev_bypass``

When DEBUG=False the same conditions must raise the existing
``plan_not_available`` exception. The bypass is a development
affordance; production behaviour is unchanged.
"""
from unittest.mock import patch

import pytest

from apps.accounts.tests.factories import UserFactory
from apps.billing.models import Subscription
from apps.billing.services.stripe_service import StripeService
from core.exceptions import GrowthPilotException


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.mark.django_db
class TestDevBypassEnabled:
    def test_no_secret_key_grants_pro(self, user, settings):
        settings.DEBUG = True
        settings.STRIPE_SECRET_KEY = ""
        settings.STRIPE_PRO_PRICE_ID = "price_123"  # has price id but no secret
        url = StripeService.create_checkout_session(
            user=user, plan="pro", annual=False,
            success_url="https://example.com/success",
            cancel_url="https://example.com/cancel",
        )
        assert "session_id=dev_bypass" in url
        sub = Subscription.objects.get(user=user)
        assert sub.plan == "pro"
        assert sub.status == "active"
        assert sub.stripe_subscription_id.startswith("dev_bypass_")

    def test_no_price_id_grants_pro(self, user, settings):
        settings.DEBUG = True
        settings.STRIPE_SECRET_KEY = "sk_test_xxx"
        settings.STRIPE_PRO_PRICE_ID = ""  # has secret but no price id
        url = StripeService.create_checkout_session(
            user=user, plan="pro", annual=False,
            success_url="https://example.com/success",
            cancel_url="https://example.com/cancel",
        )
        assert "session_id=dev_bypass" in url
        assert Subscription.objects.filter(user=user, plan="pro", status="active").exists()

    def test_appends_session_id_with_existing_query(self, user, settings):
        settings.DEBUG = True
        settings.STRIPE_SECRET_KEY = ""
        url = StripeService.create_checkout_session(
            user=user, plan="pro", annual=False,
            success_url="https://example.com/success?ref=onboarding",
            cancel_url="https://example.com/cancel",
        )
        assert url == "https://example.com/success?ref=onboarding&session_id=dev_bypass"

    def test_re_running_checkout_changes_plan_in_place(self, user, settings):
        # Bypass once — user is now on starter.
        settings.DEBUG = True
        settings.STRIPE_SECRET_KEY = ""
        StripeService.create_checkout_session(
            user=user, plan="starter", annual=False,
            success_url="https://example.com/success",
            cancel_url="https://example.com/cancel",
        )
        assert Subscription.objects.get(user=user).plan == "starter"
        # Bypass again with a different plan — should upgrade in place.
        StripeService.create_checkout_session(
            user=user, plan="pro", annual=False,
            success_url="https://example.com/success",
            cancel_url="https://example.com/cancel",
        )
        assert Subscription.objects.get(user=user).plan == "pro"

    def test_does_not_call_stripe_sdk(self, user, settings):
        settings.DEBUG = True
        settings.STRIPE_SECRET_KEY = ""
        with patch("apps.billing.services.stripe_service.stripe") as mock_stripe:
            StripeService.create_checkout_session(
                user=user, plan="pro", annual=False,
                success_url="https://example.com/s", cancel_url="https://example.com/c",
            )
            mock_stripe.checkout.Session.create.assert_not_called()


@pytest.mark.django_db
class TestDevBypassDisabledInProduction:
    def test_no_secret_in_prod_raises(self, user, settings):
        # DEBUG=False — the bypass branch must NOT fire.
        settings.DEBUG = False
        settings.STRIPE_SECRET_KEY = ""
        settings.STRIPE_PRO_PRICE_ID = ""
        with pytest.raises((GrowthPilotException, Exception)):
            StripeService.create_checkout_session(
                user=user, plan="pro", annual=False,
                success_url="https://example.com/s", cancel_url="https://example.com/c",
            )
        assert not Subscription.objects.filter(user=user).exists()

    def test_secret_present_no_price_in_prod_raises(self, user, settings):
        settings.DEBUG = False
        settings.STRIPE_SECRET_KEY = "sk_live_xxx"
        settings.STRIPE_PRO_PRICE_ID = ""
        # Plan has no price id → existing plan_not_available exception path.
        with pytest.raises(GrowthPilotException) as exc_info:
            StripeService.create_checkout_session(
                user=user, plan="pro", annual=False,
                success_url="https://example.com/s", cancel_url="https://example.com/c",
            )
        assert "not available" in str(exc_info.value).lower()
