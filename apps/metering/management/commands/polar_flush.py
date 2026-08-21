"""Flush the Polar event outbox from the command line.

The dev-machine path (docker compose runs no Celery workers) and the
sandbox smoke driver:

    manage.py polar_flush            # drain once
    manage.py polar_flush --loop 30  # drain every 30s until interrupted
"""
import time

from django.core.management.base import BaseCommand, CommandError

from apps.metering.models import PolarEventOutbox
from apps.metering.services.events import ingest_mode
from apps.metering.tasks import flush_outbox_once


class Command(BaseCommand):
    help = "Deliver pending Polar usage events from the outbox."

    def add_arguments(self, parser):
        parser.add_argument(
            "--loop",
            type=int,
            default=0,
            metavar="SECONDS",
            help="Keep flushing every N seconds until interrupted.",
        )

    def handle(self, *args, **options):
        if ingest_mode() == "off":
            raise CommandError(
                "POLAR_INGEST_MODE is 'off' — nothing is being staged. "
                "Set POLAR_ACCESS_TOKEN (and optionally POLAR_INGEST_MODE=inline)."
            )
        interval = options["loop"]
        while True:
            result = flush_outbox_once()
            pending = PolarEventOutbox.objects.filter(
                status=PolarEventOutbox.STATUS_PENDING
            ).count()
            self.stdout.write(
                f"sent={result['sent']} skipped={result['skipped']} pending={pending}"
            )
            if not interval:
                break
            time.sleep(interval)
