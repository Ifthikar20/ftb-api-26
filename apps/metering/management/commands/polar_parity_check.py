"""Compare local ledger sums against Polar meter totals per user.

    manage.py polar_parity_check
    manage.py polar_parity_check --user <uuid>

The gate for flipping POLAR_READS_ENABLED: exits 1 when any user's
current-period token drift exceeds 1% (or when Polar is unreachable).
Undelivered outbox rows are reported — drift is expected until the
outbox is drained.
"""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Sum
from django.utils import timezone

from apps.accounts.models import AITokenUsage
from apps.metering import polar_client
from apps.metering.models import PolarEventOutbox
from apps.metering.services.periods import billing_period_for


class Command(BaseCommand):
    help = "Compare current-period ledger sums vs Polar meter totals."

    def add_arguments(self, parser):
        parser.add_argument("--user", default=None, help="Limit to one user id")
        parser.add_argument(
            "--tolerance", type=float, default=1.0, help="Allowed drift percent (default 1.0)"
        )

    def handle(self, *args, **options):
        meter_id = settings.POLAR_METER_TOKENS_ID
        if not meter_id:
            raise CommandError("POLAR_METER_TOKENS_ID is not set (run polar_bootstrap).")
        if not polar_client.is_configured():
            raise CommandError("POLAR_ACCESS_TOKEN is not set.")

        pending = PolarEventOutbox.objects.filter(
            status=PolarEventOutbox.STATUS_PENDING
        ).count()
        dead = PolarEventOutbox.objects.filter(status=PolarEventOutbox.STATUS_DEAD).count()
        if pending:
            self.stdout.write(
                self.style.WARNING(f"{pending} outbox rows still pending — flush first.")
            )
        if dead:
            self.stdout.write(self.style.WARNING(f"{dead} outbox rows are dead — inspect them."))

        User = get_user_model()
        users = User.objects.filter(ai_token_usage__isnull=False).distinct()
        if options["user"]:
            users = users.filter(id=options["user"])

        tolerance = options["tolerance"]
        failures = 0
        now = timezone.now()
        self.stdout.write(f"{'user':<40} {'ledger':>14} {'polar':>14} {'drift%':>8}")
        for user in users.iterator():
            # Users Polar permanently rejected (no customer marker, e.g.
            # dev accounts on undeliverable email domains) are local-only
            # by design: the reader never consults Polar for them, so
            # they cannot drift. Report, don't fail.
            from apps.metering.models import PolarCustomer

            provisioned = (
                PolarCustomer.objects.filter(
                    user=user, environment=settings.POLAR_ENVIRONMENT
                )
                .exclude(polar_customer_id="")
                .exists()
            )
            if not provisioned:
                self.stdout.write(
                    f"{str(user.id):<40} {'(local-only: no Polar customer)':>38}"
                )
                continue
            period = billing_period_for(user)
            ledger = (
                AITokenUsage.objects.filter(user=user, created_at__gte=period.start)
                .aggregate(t=Sum("total_tokens"))["t"]
                or 0
            )
            try:
                resp = polar_client.meter_quantities(
                    meter_id,
                    start=period.start,
                    end=min(period.end, now),
                    interval="day",
                    external_customer_id=str(user.id),
                )
                polar_total = int(getattr(resp, "total", 0) or 0)
            except (polar_client.PolarUnavailable, polar_client.PolarRejected) as exc:
                raise CommandError(f"Polar read failed: {exc}") from exc

            if ledger == 0 and polar_total == 0:
                continue
            drift = abs(ledger - polar_total) / max(ledger, polar_total) * 100
            flag = ""
            if drift > tolerance:
                failures += 1
                flag = "  DRIFT"
            self.stdout.write(
                f"{str(user.id):<40} {ledger:>14,} {polar_total:>14,} {drift:>7.2f}{flag}"
            )

        if failures:
            raise CommandError(
                f"{failures} user(s) exceed {tolerance}% drift. Keep POLAR_READS_ENABLED off."
            )
        self.stdout.write(self.style.SUCCESS("Parity OK — safe to enable POLAR_READS_ENABLED."))
