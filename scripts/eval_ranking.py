"""
Offline evaluation harness for the LLM ranking model.

Reports NDCG@5 and MRR over completed audits using the predicted ranking
(``audit.brand_strengths`` from Plackett-Luce) against the empirical ranking
derived from per-prompt mention positions across providers.

Usage:
    python manage.py shell -c "exec(open('scripts/eval_ranking.py').read())"

Or import and call ``evaluate(limit=...)`` from a custom script.
"""
from __future__ import annotations

import math
from collections import defaultdict


def dcg(relevances: list[float]) -> float:
    return sum(rel / math.log2(i + 2) for i, rel in enumerate(relevances))


def ndcg_at_k(
    predicted: list[str],
    relevance: dict[str, float],
    k: int = 5,
) -> float:
    pred_rel = [relevance.get(b, 0.0) for b in predicted[:k]]
    ideal_rel = sorted(relevance.values(), reverse=True)[:k]
    idcg = dcg(ideal_rel)
    return dcg(pred_rel) / idcg if idcg > 0 else 0.0


def evaluate(limit: int = 200) -> dict:
    """Run the evaluation against the most recent ``limit`` completed audits."""
    from apps.llm_ranking.models import LLMRankingAudit

    audits = (
        LLMRankingAudit.objects
        .filter(status=LLMRankingAudit.STATUS_COMPLETED)
        .prefetch_related("results")
        .order_by("-created_at")[:limit]
    )

    ndcgs: list[float] = []
    mrrs: list[float] = []
    audits_with_signal = 0

    for audit in audits:
        strengths = audit.brand_strengths or {}
        if not strengths:
            continue
        audits_with_signal += 1
        predicted = sorted(strengths, key=strengths.get, reverse=True)

        per_prompt: dict[str, list[tuple[str, int]]] = defaultdict(list)
        for r in audit.results.all():
            if not (r.query_succeeded and r.mention_rank):
                continue
            if r.is_mentioned:
                per_prompt[r.prompt].append((audit.business_name, int(r.mention_rank)))
            for c in r.competitors_mentioned or []:
                if not isinstance(c, dict):
                    continue
                pos = c.get("position")
                name = (c.get("name") or "").strip()
                if name and pos:
                    try:
                        per_prompt[r.prompt].append((name, int(pos)))
                    except (TypeError, ValueError):
                        continue

        for items in per_prompt.values():
            if not items:
                continue
            agg: dict[str, list[int]] = defaultdict(list)
            for brand, pos in items:
                agg[brand].append(pos)
            relevance = {b: 1.0 / (sum(ps) / len(ps)) for b, ps in agg.items()}
            ndcgs.append(ndcg_at_k(predicted, relevance, k=5))
            if audit.business_name in predicted:
                mrrs.append(1.0 / (predicted.index(audit.business_name) + 1))

    summary = {
        "audits_evaluated": audits_with_signal,
        "prompts_evaluated": len(ndcgs),
        "ndcg_at_5": (sum(ndcgs) / len(ndcgs)) if ndcgs else 0.0,
        "mrr": (sum(mrrs) / len(mrrs)) if mrrs else 0.0,
    }
    print(
        f"Audits evaluated:   {summary['audits_evaluated']}\n"
        f"Prompts evaluated:  {summary['prompts_evaluated']}\n"
        f"NDCG@5:             {summary['ndcg_at_5']:.3f}\n"
        f"MRR:                {summary['mrr']:.3f}"
    )
    return summary


if __name__ == "__main__":
    evaluate()
