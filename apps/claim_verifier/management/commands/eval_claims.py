"""Run the claim-extraction eval from the CLI.

    python manage.py eval_claims [--dataset PATH]

Loads JSONL labeled examples, runs the production extractor, prints
overall precision / recall / F1 plus a per-case breakdown.
"""
from __future__ import annotations

import json

from django.core.management.base import BaseCommand

from apps.claim_verifier.eval.dataset import DEFAULT_DATASET_PATH
from apps.claim_verifier.eval.runner import run_eval


def _default_extract(text: str) -> list[dict]:
    """Default extract_fn — invokes the production extractor's LLM call.

    Returns a list of raw {subject, predicate, object, confidence} dicts.
    Brand context is left blank so every triple is kept; the eval scoring
    cares about extraction quality, not brand filtering.
    """
    from apps.claim_verifier.services.claim_extractor import _call_llm

    try:
        return _call_llm("", text) or []
    except Exception:
        return []


class Command(BaseCommand):
    help = "Run claim-extraction eval against a labeled JSONL dataset."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dataset",
            default=DEFAULT_DATASET_PATH,
            help="Path to a JSONL eval dataset (default: bundled dataset).",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Print full results as JSON instead of a human-readable summary.",
        )

    def handle(self, *args, **options):
        dataset_path = options["dataset"]
        results = run_eval(_default_extract, dataset_path=dataset_path)

        if options["json"]:
            self.stdout.write(json.dumps(results, indent=2))
            return

        overall = results["overall"]
        self.stdout.write(self.style.SUCCESS(
            f"Eval results — {results['case_count']} case(s) from {dataset_path}",
        ))
        if results["case_count"] == 0:
            self.stdout.write(
                "No labeled cases found. Add JSONL rows to the dataset to start measuring.",
            )
            return
        self.stdout.write(
            f"  precision={overall['precision']}  recall={overall['recall']}  f1={overall['f1']}",
        )
        self.stdout.write(
            f"  tp={overall['tp']}  fp={overall['fp']}  fn={overall['fn']}",
        )
        self.stdout.write("Per case:")
        for row in results["per_case"]:
            if "error" in row:
                self.stdout.write(f"  {row['id']}: ERROR {row['error']}")
            else:
                self.stdout.write(
                    f"  {row['id']}: p={row['precision']} r={row['recall']} f1={row['f1']}",
                )
