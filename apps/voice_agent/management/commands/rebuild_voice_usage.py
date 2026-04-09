"""Rebuild VoiceUsageMonthly aggregates from CallLog.

Run after deploying the usage tracking feature so historical calls show
up on the dashboard, or any time you suspect the live increments drifted
(worker crashed mid-update, manual DB tweak, etc.).

Examples:

    # Rebuild every month for every website
    python manage.py rebuild_voice_usage

    # Just one website
    python manage.py rebuild_voice_usage --website 1234abcd-...

    # Just the current month
    python manage.py rebuild_voice_usage --month 2026-04
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Rebuild VoiceUsageMonthly rollups from CallLog."

    def add_arguments(self, parser):
        parser.add_argument("--website", help="Limit to a single website UUID.")
        parser.add_argument(
            "--month",
            help="Rebuild a single year-month (e.g. '2026-04'). Default: every month with data.",
        )

    def handle(self, *args, **options):
        from apps.voice_agent.models import CallLog
        from apps.voice_agent.services.usage_service import (
            estimate_call_cost,
            rebuild_month,
        )

        qs = CallLog.objects.all()
        if options.get("website"):
            qs = qs.filter(website_id=options["website"])

        # First pass: make sure every CallLog has its per-call cost stamped.
        # Older rows from before the usage feature won't have it, so the
        # rebuild would otherwise sum a column of zeros.
        stamped = 0
        for call in qs.filter(billable_seconds=0).iterator():
            cost = estimate_call_cost(call)
            call.billable_seconds = cost.billable_seconds
            if not call.stt_seconds:
                call.stt_seconds = call.duration_seconds or 0
            call.estimated_cost_usd = cost.total_usd
            call.save(update_fields=[
                "billable_seconds", "stt_seconds", "estimated_cost_usd", "updated_at",
            ])
            stamped += 1
        if stamped:
            self.stdout.write(self.style.NOTICE(f"Stamped per-call cost on {stamped} call(s)."))

        # Determine which (website, month) pairs to rebuild.
        if options.get("month"):
            months = {options["month"]}
            qs = qs.filter(
                created_at__year=int(options["month"].split("-")[0]),
                created_at__month=int(options["month"].split("-")[1]),
            )
        else:
            months = set()

        pairs = set()
        for call in qs.values_list("website_id", "created_at"):
            wid, created_at = call
            ym = (created_at or timezone.now()).strftime("%Y-%m")
            if months and ym not in months:
                continue
            pairs.add((wid, ym))

        for wid, ym in sorted(pairs, key=lambda p: (str(p[0]), p[1])):
            row = rebuild_month(wid, ym)
            self.stdout.write(
                f"  website={wid} month={ym} -> "
                f"{row.total_calls} calls, {row.billable_minutes}m, ${row.estimated_cost_usd}"
            )

        self.stdout.write(self.style.SUCCESS(
            f"Rebuilt {len(pairs)} (website, month) rollup(s)."
        ))
