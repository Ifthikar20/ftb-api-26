"""Stage historical ledger rows for delivery to Polar.

    manage.py polar_backfill --since 2026-08-01
    manage.py polar_backfill --since 2026-08-01 --user <uuid>

Creates outbox rows for AITokenUsage records that have none yet. Rows
recorded before the idempotency-key migration get a synthetic
`backfill:<usage-id>` key (stable, so re-running is safe).

CAVEAT (printed loudly): Polar attributes events to billing periods by
INGESTION time. Backfilled events all land in "today's" Polar bucket —
period totals come out right only when you backfill the CURRENT period;
older history should stay local-ledger-only.
"""
from datetime import datetime
from datetime import time as dtime

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.accounts.models import AITokenUsage
from apps.metering.models import PolarEventOutbox
from apps.metering.services.events import build_event, ingest_mode


class Command(BaseCommand):
    help = "Create outbox rows for historical AITokenUsage records."

    def add_arguments(self, parser):
        parser.add_argument("--since", required=True, help="ISO date, e.g. 2026-08-01")
        parser.add_argument("--user", default=None, help="Limit to one user id")
        parser.add_argument(
            "--dry-run", action="store_true", help="Count only; stage nothing."
        )

    def handle(self, *args, **options):
        if ingest_mode() == "off":
            raise CommandError("POLAR_INGEST_MODE is 'off' — enable ingestion first.")
        try:
            since_date = datetime.strptime(options["since"], "%Y-%m-%d").date()
        except ValueError as exc:
            raise CommandError("--since must be YYYY-MM-DD") from exc
        since = timezone.make_aware(datetime.combine(since_date, dtime.min))

        self.stdout.write(
            self.style.WARNING(
                "NOTE: Polar attributes events by ingestion time. Backfill the "
                "current billing period only; older usage should stay local."
            )
        )

        qs = (
            AITokenUsage.objects.filter(created_at__gte=since, user__isnull=False)
            .filter(polar_outbox__isnull=True)
            .order_by("created_at")
        )
        if options["user"]:
            qs = qs.filter(user_id=options["user"])

        total = qs.count()
        if options["dry_run"]:
            self.stdout.write(f"Would stage {total} ledger rows.")
            return

        staged = 0
        for usage in qs.iterator(chunk_size=1000):
            if not usage.idempotency_key:
                usage.idempotency_key = f"backfill:{usage.id}"
                usage.save(update_fields=["idempotency_key"])
            event = build_event(usage)
            _, created = PolarEventOutbox.objects.get_or_create(
                idempotency_key=usage.idempotency_key,
                defaults={
                    "usage": usage,
                    "external_customer_id": event["external_customer_id"],
                    "name": event["name"],
                    "payload": event,
                },
            )
            staged += 1 if created else 0

        self.stdout.write(
            self.style.SUCCESS(f"Staged {staged}/{total} rows. Run polar_flush to deliver.")
        )
