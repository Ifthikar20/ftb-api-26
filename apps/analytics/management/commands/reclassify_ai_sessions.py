"""One-off repair for sessions mislabeled by the old UTM precedence.

Before the fix in EventIngestionService._parse_utm, a link tagged
``?utm_source=chatgpt.com`` bypassed the AI-referrer classifier and the
session was stored with source="chatgpt.com", medium="" — invisible to
every medium="ai" query. This command rewrites those historical rows to
the canonical AI source and medium. Idempotent: rows already labeled
medium="ai" are never touched.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.analytics.models import Session
from apps.analytics.services.event_ingestion_service import _AI_UTM_SOURCES


class Command(BaseCommand):
    help = (
        "Relabel historical sessions whose source names an AI assistant "
        "(e.g. chatgpt.com) but whose medium is not 'ai'."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Report what would change without writing.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        total = 0
        # Group by raw stored value so each canonical target is one UPDATE.
        by_raw: dict[str, str] = {}
        for raw, canonical in _AI_UTM_SOURCES.items():
            by_raw[raw] = canonical
            by_raw[f"www.{raw}"] = canonical

        for raw, canonical in by_raw.items():
            qs = Session.objects.filter(source__iexact=raw).exclude(medium="ai")
            count = qs.count()
            if not count:
                continue
            total += count
            if dry_run:
                self.stdout.write(f"would relabel {count} sessions: {raw} -> {canonical}/ai")
            else:
                qs.update(source=canonical, medium="ai")
                self.stdout.write(f"relabeled {count} sessions: {raw} -> {canonical}/ai")

        verb = "would relabel" if dry_run else "relabeled"
        self.stdout.write(self.style.SUCCESS(f"{verb} {total} session(s) total"))
