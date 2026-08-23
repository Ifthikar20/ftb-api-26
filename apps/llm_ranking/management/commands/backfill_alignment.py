"""Backfill brand-alignment scores for historical responses.

Mirrors the reextract staleness pattern: rows are due when they were
never analyzed (alignment_version == "") or were analyzed under an older
schema version. The analysis stamps rows even on skip statuses, so a
second run is a no-op.

Run once after deploying the alignment feature:
    python manage.py backfill_alignment [--website <uuid>] [--limit 500] [--dry-run]
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db.models import Q

from apps.brand_vault.services.brand_alignment import ALIGNMENT_VERSION, compute_alignment
from apps.llm_ranking.models import LLMRankingResult


class Command(BaseCommand):
    help = "Score historical LLM responses against the brand knowledge base."

    def add_arguments(self, parser):
        parser.add_argument("--website", default="", help="Limit to one website id.")
        parser.add_argument("--limit", type=int, default=500)
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Report how many rows are due without analyzing.",
        )

    def handle(self, *args, **options):
        stale = Q(alignment_version="") | ~Q(alignment_version=ALIGNMENT_VERSION)
        qs = (
            LLMRankingResult.objects
            .filter(query_succeeded=True)
            .exclude(response_text="")
            .filter(stale)
            .select_related("audit__website", "audit__created_by")
            .order_by("created_at")
        )
        if options["website"]:
            qs = qs.filter(audit__website_id=options["website"])
        rows = list(qs[: options["limit"]])

        if options["dry_run"]:
            self.stdout.write(self.style.SUCCESS(f"{len(rows)} row(s) due for alignment"))
            return

        statuses: dict[str, int] = {}
        for result in rows:
            try:
                outcome = compute_alignment(result)
            except Exception as exc:
                self.stderr.write(f"failed for {result.id}: {exc}")
                continue
            result.alignment_score = outcome.score
            result.alignment_detail = outcome.detail
            result.alignment_model = outcome.model
            result.alignment_version = outcome.version
            result.save(update_fields=[
                "alignment_score", "alignment_detail", "alignment_model",
                "alignment_version", "updated_at",
            ])
            statuses[outcome.status] = statuses.get(outcome.status, 0) + 1

        summary = ", ".join(f"{k}={v}" for k, v in sorted(statuses.items())) or "nothing to do"
        self.stdout.write(self.style.SUCCESS(f"analyzed {len(rows)} row(s): {summary}"))
