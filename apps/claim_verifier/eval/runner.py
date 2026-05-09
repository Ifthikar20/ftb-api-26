"""Run the claim-extraction eval and compute precision / recall / F1.

Triple-match semantics: a predicted claim is considered correct iff a
case-insensitive (subject, predicate, object) triple matches an entry
in ``expected_claims``. Trims whitespace, lowercases, and strips
trailing punctuation before comparing.
"""
from __future__ import annotations

from typing import Callable, Iterable

from apps.claim_verifier.eval.dataset import (
    DEFAULT_DATASET_PATH,
    EvalCase,
    load_dataset,
)


def _norm(value: str) -> str:
    return (value or "").strip().strip(".,;:!?").lower()


def _triple(item: dict) -> tuple[str, str, str]:
    return (
        _norm(item.get("subject") or ""),
        _norm(item.get("predicate") or ""),
        _norm(item.get("object") or ""),
    )


def _score_case(predicted: Iterable[dict], expected: Iterable[dict]) -> dict:
    pred_set = {_triple(p) for p in predicted}
    exp_set = {_triple(e) for e in expected}
    tp = len(pred_set & exp_set)
    fp = len(pred_set - exp_set)
    fn = len(exp_set - pred_set)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {
        "tp": tp, "fp": fp, "fn": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def run_eval(
    extract_fn: Callable[[str], list[dict]],
    dataset_path: str = DEFAULT_DATASET_PATH,
) -> dict:
    """Run ``extract_fn`` over every case and return aggregated metrics.

    ``extract_fn`` should accept a response text and return a list of
    ``{subject, predicate, object}`` dicts. Returns an aggregated metrics
    block plus a per-case breakdown.
    """
    cases: list[EvalCase] = load_dataset(dataset_path)
    if not cases:
        return {
            "dataset_path": dataset_path,
            "case_count": 0,
            "overall": {"tp": 0, "fp": 0, "fn": 0,
                        "precision": 0.0, "recall": 0.0, "f1": 0.0},
            "per_case": [],
        }

    per_case: list[dict] = []
    total_tp = total_fp = total_fn = 0
    for case in cases:
        try:
            predicted = list(extract_fn(case.response_text) or [])
        except Exception as exc:
            per_case.append({"id": case.id, "error": str(exc)})
            continue
        scores = _score_case(predicted, case.expected_claims)
        total_tp += scores["tp"]
        total_fp += scores["fp"]
        total_fn += scores["fn"]
        per_case.append({"id": case.id, **scores})

    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) else 0.0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {
        "dataset_path": dataset_path,
        "case_count": len(cases),
        "overall": {
            "tp": total_tp, "fp": total_fp, "fn": total_fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        },
        "per_case": per_case,
    }
