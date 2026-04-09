"""Re-run lead scoring on existing completed CallLog rows.

Use after deploying the lead detection feature so historical calls also
populate the Lead Detection tab. Safe to run repeatedly — scoring is
idempotent and ignores already-promoted/dismissed calls when flagging.

Examples:

    # Score every completed call across every website
    python manage.py rescore_voice_calls

    # Score only one website
    python manage.py rescore_voice_calls --website 1234abcd-...

    # Score and print a per-call summary
    python manage.py rescore_voice_calls --verbose

    # Dry run — compute scores but don't persist them
    python manage.py rescore_voice_calls --dry-run
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Backfill is_possible_lead/lead_score on existing CallLog rows."

    def add_arguments(self, parser):
        parser.add_argument(
            "--website",
            help="Limit to a single website by UUID.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Compute scores in memory but do not save them.",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Print one line per call instead of just the totals.",
        )

    def handle(self, *args, **options):
        from apps.voice_agent.models import CallLog
        from apps.voice_agent.services.lead_scoring_service import score_call

        qs = CallLog.objects.filter(
            status=CallLog.STATUS_COMPLETED,
        ).exclude(transcript="").order_by("-created_at")

        website_id = options.get("website")
        if website_id:
            qs = qs.filter(website_id=website_id)
            if not qs.exists():
                raise CommandError(
                    f"No completed calls with transcripts found for website {website_id}."
                )

        dry_run = options["dry_run"]
        verbose = options["verbose"]

        total = 0
        flagged = 0
        for call in qs.iterator():
            total += 1
            score_call(call, persist=not dry_run)
            if call.is_possible_lead:
                flagged += 1
            if verbose:
                self.stdout.write(
                    f"  call={call.id} score={call.lead_score} "
                    f"flagged={call.is_possible_lead} "
                    f"signals={list(call.lead_signals.keys())}"
                )

        verb = "Would flag" if dry_run else "Flagged"
        self.stdout.write(self.style.SUCCESS(
            f"Scored {total} call(s). {verb} {flagged} as possible leads."
        ))
