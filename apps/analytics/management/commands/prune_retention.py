"""Run the retention pruners from the command line.

Exists so the first production pass can be inspected before beat is allowed
to fire it. The backlog is large -- nothing has ever pruned these tables --
so always run with --dry-run first and read the counts.

    manage.py prune_retention --dry-run
    manage.py prune_retention --dry-run --llm
    manage.py prune_retention            # deletes analytics rows
"""
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.analytics.tasks import prune_analytics_events, prune_llm_results


class Command(BaseCommand):
    help = "Apply the configured retention windows. Use --dry-run to preview."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be deleted without deleting it.",
        )
        parser.add_argument(
            "--llm",
            action="store_true",
            help="Also prune stored LLM answers and brand-security findings.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        self.stdout.write("Retention windows in effect:")
        for name in (
            "ANALYTICS_RETENTION_DAYS",
            "ACCESS_LOG_RETENTION_DAYS",
            "LLM_RESULT_RETENTION_DAYS",
            "SAFETY_ALERT_RETENTION_DAYS",
        ):
            self.stdout.write(f"  {name} = {getattr(settings, name)}")
        if getattr(settings, "LLM_WEBSEARCH_ENABLED", False):
            self.stdout.write(
                self.style.WARNING(
                    "  LLM_WEBSEARCH_ENABLED is on: Gemini rows are Grounded "
                    f"Results and cap at {settings.GROUNDED_RESULT_MAX_RETENTION_DAYS} days."
                )
            )

        if dry_run:
            self.stdout.write(self.style.WARNING("\nDRY RUN -- nothing will be deleted.\n"))

        self._report("analytics", prune_analytics_events(dry_run=dry_run))
        if options["llm"]:
            self._report("llm", prune_llm_results(dry_run=dry_run))

    def _report(self, label, result):
        self.stdout.write(f"\n{label}:")
        for key, value in result.items():
            if isinstance(value, int):
                self.stdout.write(f"  {key}: {value}")
        if not result.get("dry_run"):
            self.stdout.write(self.style.SUCCESS(f"{label} prune applied."))
