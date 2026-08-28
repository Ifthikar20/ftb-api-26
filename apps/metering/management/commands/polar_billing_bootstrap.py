"""Create the Pro subscription products in Polar and print their ids.

Run once per environment (sandbox first):

    manage.py polar_billing_bootstrap

Idempotent: existing products with the canonical names are reused.
Requires an access token with products scopes; if the current token was
minted with only the metering scopes, create a new token including
products:read/write, checkouts:read/write, subscriptions:read/write and
customer_sessions:write.
"""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.billing.services import polar_billing
from apps.metering import polar_client


class Command(BaseCommand):
    help = "Create the Cansee Pro products (monthly/annual) in Polar."

    def handle(self, *args, **options):
        if not polar_client.is_configured():
            raise CommandError("POLAR_ACCESS_TOKEN is not set.")

        self.stdout.write(f"Environment: {settings.POLAR_ENVIRONMENT}")
        try:
            products = polar_billing.bootstrap_products()
        except polar_client.PolarRejected as exc:
            raise CommandError(
                f"Polar rejected the request: {exc}\n"
                "If this is a 403, the access token lacks the products "
                "scopes - create a new token including products:read/write, "
                "checkouts:read/write, subscriptions:read/write and "
                "customer_sessions:write."
            ) from exc
        except polar_client.PolarUnavailable as exc:
            raise CommandError(f"Polar unreachable: {exc}") from exc

        self.stdout.write(self.style.SUCCESS("Products ready:"))
        for name, product_id in products.items():
            self.stdout.write(f"  {name}: {product_id}")
        self.stdout.write("")
        self.stdout.write("Add to the environment:")
        self.stdout.write(
            f"  POLAR_PRODUCT_PRO_MONTHLY_ID={products[polar_billing.PRODUCT_PRO_MONTHLY]}"
        )
        self.stdout.write(
            f"  POLAR_PRODUCT_PRO_ANNUAL_ID={products[polar_billing.PRODUCT_PRO_ANNUAL]}"
        )
