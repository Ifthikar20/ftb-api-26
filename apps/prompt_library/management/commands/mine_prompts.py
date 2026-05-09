"""Run the prompt miners against every active industry.

Default behaviour mines Reddit only — the public JSON endpoint needs
no credentials. Pass ``--sources`` to add SerpAPI / LLM synthesis when
keys are configured.

Usage:
    python manage.py mine_prompts                       # all industries, reddit only
    python manage.py mine_prompts --sources reddit serpapi
    python manage.py mine_prompts --industry nonprofit  # one industry
    python manage.py mine_prompts --limit 60            # rows per source per industry
"""
from __future__ import annotations

import time

from django.core.management.base import BaseCommand

from apps.prompt_library.models import Industry
from apps.prompt_library.services.miner_service import mine_for_industry


class Command(BaseCommand):
    help = "Mine demand-side prompts from Reddit/SerpAPI and persist them."

    def add_arguments(self, parser):
        parser.add_argument("--industry", default=None, help="Slug of a single industry to mine.")
        parser.add_argument(
            "--sources",
            nargs="+",
            default=["reddit"],
            help="Miners to run. Choices: reddit, serpapi, llm_synth.",
        )
        parser.add_argument("--limit", type=int, default=40)
        parser.add_argument(
            "--sleep", type=float, default=1.5,
            help="Seconds to sleep between industries — keeps Reddit happy.",
        )

    def handle(self, *args, **opts):
        qs = Industry.objects.filter(is_active=True).order_by("name")
        if opts["industry"]:
            qs = qs.filter(slug=opts["industry"])
        if not qs.exists():
            self.stderr.write(self.style.ERROR("No matching industries."))
            return

        total = 0
        for industry in qs:
            summary = mine_for_industry(
                industry,
                sources=tuple(opts["sources"]),
                limit=opts["limit"],
            )
            count = sum(summary.values())
            total += count
            self.stdout.write(
                self.style.SUCCESS(
                    f"{industry.slug:35s} {summary} (+{count})"
                )
            )
            time.sleep(opts["sleep"])

        self.stdout.write(self.style.SUCCESS(f"Done. {total} new prompts."))
