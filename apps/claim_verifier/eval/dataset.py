"""Eval dataset loader for the claim extractor.

Stores gold-standard atomic claims for a curated set of LLM responses.
Lives as a JSONL file so it is easy to grow incrementally without a
schema migration. Empty file is valid (returns []).
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import List

DEFAULT_DATASET_PATH = os.path.join(
    os.path.dirname(__file__), "dataset.jsonl",
)


@dataclass
class EvalCase:
    """One labeled example for the claim-extraction eval."""

    id: str
    response_text: str
    expected_claims: List[dict] = field(default_factory=list)
    notes: str = ""


def load_dataset(path: str = DEFAULT_DATASET_PATH) -> List[EvalCase]:
    """Load JSONL dataset. Empty list if file is missing or empty."""
    cases: list[EvalCase] = []
    if not path or not os.path.exists(path):
        return cases
    with open(path, "r", encoding="utf-8") as fh:
        for line_no, raw in enumerate(fh, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            cases.append(EvalCase(
                id=str(data.get("id") or f"case-{line_no}"),
                response_text=data.get("response_text") or "",
                expected_claims=list(data.get("expected_claims") or []),
                notes=data.get("notes") or "",
            ))
    return cases
