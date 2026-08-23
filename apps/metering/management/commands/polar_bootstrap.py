"""Validate the Polar connection and create the two canonical meters.

Run once per environment (sandbox first):

    manage.py polar_bootstrap

Prints the meter ids to paste into the env as POLAR_METER_TOKENS_ID /
POLAR_METER_SPEND_ID. Idempotent: existing meters with the canonical
names are reused, never recreated.
"""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.metering import polar_client


class Command(BaseCommand):
    help = "Validate Polar credentials and create the llm-tokens / ai-spend-micros meters."

    def handle(self, *args, **options):
        if not polar_client.is_configured():
            raise CommandError(
                "POLAR_ACCESS_TOKEN is not set. Create an organization access "
                "token in the Polar dashboard (sandbox.polar.sh for sandbox) "
                "and export it first."
            )

        self.stdout.write(f"Environment: {settings.POLAR_ENVIRONMENT}")
        try:
            meters = polar_client.bootstrap_meters()
        except polar_client.PolarRejected as exc:
            raise CommandError(f"Polar rejected the meter definition: {exc}") from exc
        except polar_client.PolarUnavailable as exc:
            raise CommandError(f"Polar unreachable: {exc}") from exc

        self.stdout.write(self.style.SUCCESS("Meters ready:"))
        for name, meter_id in meters.items():
            self.stdout.write(f"  {name}: {meter_id}")
        self.stdout.write("")
        self.stdout.write("Add to the environment:")
        self.stdout.write(f"  POLAR_METER_TOKENS_ID={meters[polar_client.METER_TOKENS_NAME]}")
        self.stdout.write(f"  POLAR_METER_SPEND_ID={meters[polar_client.METER_SPEND_NAME]}")
        if settings.POLAR_INGEST_MODE == "off":
            self.stdout.write(
                self.style.WARNING(
                    "POLAR_INGEST_MODE resolves to 'off' — set it to 'celery' "
                    "(prod) or 'inline' (dev without workers) to start ingesting."
                )
            )
