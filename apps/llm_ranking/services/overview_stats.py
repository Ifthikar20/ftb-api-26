"""Overview-tab aggregates for the dashboard.

Builds the four cards the Overview tab renders — top brands, the
brand-vs-model performance matrix, top cited domains, and the domain-type
split — from completed audits only.

Everything is derived. When the user has no completed audits (or no
audits inside the requested window) the builder returns ``has_data:
False`` with empty collections, and the frontend renders guidance
pointing at the action that would produce data. Nothing in this module
invents representative numbers to fill a layout: an empty dashboard is
the correct rendering of an account that has not measured anything yet.

Metric definitions, kept here so the frontend stays in sync:

* visibility -- share of a brand's answers where the brand was mentioned.
  For the target brand this is ``is_mentioned`` over all results; for a
  competitor it is how many results named it over the same denominator.
* sov        -- share of voice: a brand's mentions as a percentage of all
  brand mentions (target + competitors) in the window.
* position   -- mean rank when mentioned, lower is better. Only the target
  brand records a rank, so competitors report their mean listed position.
* sentiment  -- 0-100 net score over answers that mentioned the brand,
  positive counting 100, neutral 50, negative 0.
* trend      -- percentage change in visibility against the preceding
  window of equal length. Omitted (``None``) when there is no prior
  window to compare against, so the UI can hide the delta rather than
  print a fabricated +0%.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from apps.citations.models import Citation
from apps.citations.services.url_analytics import domain_type_for
from apps.llm_ranking.models import LLMRankingAudit, LLMRankingResult

# Matrix columns are labelled with the short provider name rather than the
# verbose choice label ("Claude (Anthropic)" does not fit a table header).
PROVIDER_LABELS = {
    "claude": "Claude",
    "gpt4": "ChatGPT",
    "gemini": "Gemini",
    "perplexity": "Perplexity",
    "meta_llama": "Llama",
    "mistral": "Mistral",
    "cohere": "Cohere",
    "deepseek": "DeepSeek",
    "grok": "Grok",
    "amazon_nova": "Nova",
}

# Matching the frontend legend in DomainTypesCard.
DOMAIN_TYPE_COLORS = {
    "Corporate": "var(--chart-1)",
    "UGC": "var(--chart-2)",
    "Editorial": "var(--chart-3)",
    "Reference": "var(--chart-4)",
}

_SENTIMENT_SCORE = {
    LLMRankingResult.SENTIMENT_POSITIVE: 100.0,
    LLMRankingResult.SENTIMENT_NEUTRAL: 50.0,
    LLMRankingResult.SENTIMENT_NEGATIVE: 0.0,
}

MAX_BRANDS = 10
MAX_DOMAINS = 8
MAX_MATRIX_ROWS = 8
MAX_PROMPTS = 10


def empty_overview() -> dict:
    """The no-data shape. Kept in one place so every early return matches."""
    return {
        "has_data": False,
        "brands": [],
        "domains": [],
        "domain_types": None,
        "matrix": {"models": [], "rows": []},
        "prompts": [],
        "insight_kpis": [],
        "headline": None,
    }


def build_overview_for_user(
    user,
    *,
    start: datetime | None = None,
    end: datetime | None = None,
    prompts: list[str] | None = None,
) -> dict:
    """Aggregate the Overview cards for ``user`` within an optional window."""
    audits = _audits_in(user, start, end)
    audit_ids = list(audits.values_list("id", flat=True))
    if not audit_ids:
        return empty_overview()

    results = list(_filtered_results(audit_ids, prompts))
    if not results:
        return empty_overview()

    brand_name = _target_brand_name(audits)
    brands = _build_brands(results, brand_name)
    if not brands:
        return empty_overview()

    # Trend needs the window before this one. Without an explicit window
    # there is no "preceding period" to speak of, so deltas stay None.
    previous = _previous_brand_visibility(user, start, end, prompts, brand_name)
    for row in brands:
        prior = previous.get(row["name"].lower())
        row["trend"], row["up"] = _delta(row["visibility"], prior)

    # Attach the per-brand prompt breakdown so a row in Top Brands can be
    # expanded to show what that brand actually outranked you on.
    brand_prompts = _build_brand_prompts(results, brand_name)
    for row in brands:
        row["prompts"] = brand_prompts.get(row["name"].lower(), [])
        row["beat_count"] = sum(1 for p in row["prompts"] if p["beats_you"])

    domains, domain_types = _build_domains(audit_ids)

    return {
        "has_data": True,
        "brands": brands,
        "domains": domains,
        "domain_types": domain_types,
        "matrix": _build_matrix(results, brand_name, brands),
        "prompts": _build_prompts(results),
        "insight_kpis": _build_kpis(brands, brand_name),
        "headline": _build_headline(brands, brand_name),
    }


# ── queryset helpers (mirrors geo_stats so filters behave identically) ──

def _audits_in(user, start, end):
    qs = LLMRankingAudit.objects.filter(
        created_by=user, status=LLMRankingAudit.STATUS_COMPLETED,
    )
    if start is not None:
        qs = qs.filter(completed_at__gte=start)
    if end is not None:
        qs = qs.filter(completed_at__lt=end)
    return qs


def _filtered_results(audit_ids, prompts):
    qs = LLMRankingResult.objects.filter(
        audit_id__in=audit_ids, query_succeeded=True,
    )
    if prompts:
        qs = qs.filter(prompt__in=prompts)
    return qs


def _target_brand_name(audits) -> str:
    """The brand being measured. Most recent audit wins on rename."""
    latest = audits.order_by("-completed_at").first()
    if latest and latest.business_name:
        return latest.business_name
    if latest and latest.website_id:
        return getattr(latest.website, "name", "") or ""
    return ""


# ── brands ──

def _build_brands(results, brand_name: str) -> list[dict]:
    total = len(results)
    if not total:
        return []

    target_mentions = 0
    target_ranks: list[int] = []
    target_sentiment: list[float] = []

    comp_mentions: dict[str, int] = defaultdict(int)
    comp_positions: dict[str, list[int]] = defaultdict(list)
    comp_display: dict[str, str] = {}

    for r in results:
        if r.is_mentioned:
            target_mentions += 1
            if r.mention_rank:
                target_ranks.append(r.mention_rank)
            score = _SENTIMENT_SCORE.get(r.sentiment)
            if score is not None:
                target_sentiment.append(score)

        for entry in r.competitors_mentioned or []:
            if not isinstance(entry, dict):
                continue
            name = (entry.get("name") or "").strip()
            if not name:
                continue
            key = name.lower()
            # Skip the target brand appearing in its own competitor list.
            if brand_name and key == brand_name.strip().lower():
                continue
            comp_mentions[key] += 1
            comp_display.setdefault(key, name)
            pos = entry.get("position")
            if isinstance(pos, int) and pos > 0:
                comp_positions[key].append(pos)

    all_mentions = target_mentions + sum(comp_mentions.values())
    if not all_mentions:
        return []

    rows: list[dict] = []
    if brand_name:
        rows.append({
            "name": brand_name,
            "category": "Your brand",
            "is_target": True,
            "visibility": _pct(target_mentions, total),
            "sov": _pct(target_mentions, all_mentions),
            "sentiment": round(_mean(target_sentiment)) if target_sentiment else None,
            "position": round(_mean(target_ranks), 1) if target_ranks else None,
        })

    for key, count in sorted(comp_mentions.items(), key=lambda kv: -kv[1]):
        rows.append({
            "name": comp_display[key],
            "category": "Competitor",
            "is_target": False,
            "visibility": _pct(count, total),
            "sov": _pct(count, all_mentions),
            # Competitor sentiment is not extracted per brand; the
            # extractor only scores the answer relative to the target.
            "sentiment": None,
            "position": (
                round(_mean(comp_positions[key]), 1) if comp_positions[key] else None
            ),
        })

    # Rank strictly by measured visibility. The target brand gets no
    # privileged position — if a competitor is ahead, it ranks ahead, and
    # a tie is broken alphabetically rather than in the user's favour.
    rows.sort(key=lambda r: (-r["visibility"], r["name"].lower()))
    rows = rows[:MAX_BRANDS]
    for i, row in enumerate(rows, start=1):
        row["rank"] = i
    return rows


def _previous_brand_visibility(user, start, end, prompts, brand_name) -> dict:
    """Visibility per brand over the window immediately before this one."""
    if start is None or end is None:
        return {}
    span = end - start
    prev_results = list(
        _filtered_results(
            list(
                _audits_in(user, start - span, start).values_list("id", flat=True),
            ),
            prompts,
        ),
    )
    if not prev_results:
        return {}
    return {
        row["name"].lower(): row["visibility"]
        for row in _build_brands(prev_results, brand_name)
    }


def _delta(current: float, prior: float | None):
    """Percentage change vs the prior window, plus a direction flag.

    Returns (None, None) when there is nothing to compare against so the
    UI hides the badge instead of rendering a meaningless 0%.
    """
    if prior is None or prior == 0:
        return None, None
    change = ((current - prior) / prior) * 100
    return round(abs(change), 1), change >= 0


# ── matrix ──

def _build_matrix(results, brand_name: str, brands: list[dict]) -> dict:
    """Visibility per brand per provider."""
    providers = sorted({r.provider for r in results if r.provider})
    if not providers:
        return {"models": [], "rows": []}

    totals: dict[str, int] = defaultdict(int)
    target_hits: dict[str, int] = defaultdict(int)
    comp_hits: dict[tuple, int] = defaultdict(int)

    for r in results:
        if not r.provider:
            continue
        totals[r.provider] += 1
        if r.is_mentioned:
            target_hits[r.provider] += 1
        for entry in r.competitors_mentioned or []:
            if not isinstance(entry, dict):
                continue
            name = (entry.get("name") or "").strip().lower()
            if name:
                comp_hits[(name, r.provider)] += 1

    rows = []
    for brand in brands[:MAX_MATRIX_ROWS]:
        key = brand["name"].lower()
        values = []
        for p in providers:
            denom = totals.get(p, 0)
            if not denom:
                values.append(0.0)
                continue
            hits = (
                target_hits.get(p, 0) if brand["is_target"]
                else comp_hits.get((key, p), 0)
            )
            values.append(_pct(hits, denom))
        rows.append({
            "brand": brand["name"],
            "you": brand["is_target"],
            "values": values,
        })

    return {
        "models": [PROVIDER_LABELS.get(p, p.title()) for p in providers],
        "rows": rows,
    }


# ── per-brand drill-down ──

def _build_brand_prompts(results, brand_name: str) -> dict[str, list[dict]]:
    """For each brand, the prompts it appeared in and how it placed vs you.

    A ranked list of competitors is not actionable on its own — the useful
    question is *what did they beat me on*. This maps every brand to the
    prompts where it surfaced, its position there, your position on the
    same prompt, and whether it outranked you.

    ``beats_you`` is true when the competitor placed above you, which
    includes the case where you were not mentioned at all. Position is
    rank-style: lower is better, None means mentioned without a rank.
    """
    target_key = (brand_name or "").strip().lower()
    # (brand_key, prompt) -> aggregate across providers
    acc: dict[tuple, dict] = {}
    # prompt -> your best rank, and whether you appeared at all
    your_rank: dict[str, int | None] = {}
    your_seen: dict[str, bool] = {}

    for r in results:
        prompt = (r.prompt or "").strip()
        if not prompt:
            continue
        if r.is_mentioned:
            your_seen[prompt] = True
            if r.mention_rank:
                prev = your_rank.get(prompt)
                if prev is None or r.mention_rank < prev:
                    your_rank[prompt] = r.mention_rank
        else:
            your_seen.setdefault(prompt, False)

        provider = PROVIDER_LABELS.get(r.provider, (r.provider or "").title())

        # The target brand's own row.
        if target_key and r.is_mentioned:
            row = acc.setdefault((target_key, prompt), {
                "text": prompt, "position": None, "providers": set(),
            })
            row["providers"].add(provider)
            if r.mention_rank and (row["position"] is None or r.mention_rank < row["position"]):
                row["position"] = r.mention_rank

        for entry in r.competitors_mentioned or []:
            if not isinstance(entry, dict):
                continue
            name = (entry.get("name") or "").strip()
            if not name:
                continue
            key = name.lower()
            if key == target_key:
                continue
            row = acc.setdefault((key, prompt), {
                "text": prompt, "position": None, "providers": set(),
            })
            row["providers"].add(provider)
            pos = entry.get("position")
            if isinstance(pos, int) and pos > 0:
                if row["position"] is None or pos < row["position"]:
                    row["position"] = pos

    out: dict[str, list[dict]] = defaultdict(list)
    for (key, prompt), row in acc.items():
        mine = your_rank.get(prompt)
        appeared = your_seen.get(prompt, False)
        if key == target_key:
            beats = None  # not meaningful against yourself
        elif not appeared:
            beats = True  # they surfaced, you did not
        elif row["position"] is None or mine is None:
            beats = False  # no comparable rank — don't claim a loss
        else:
            beats = row["position"] < mine

        out[key].append({
            "text": row["text"],
            "position": row["position"],
            "your_position": mine,
            "you_appeared": appeared,
            "beats_you": beats,
            "providers": sorted(row["providers"]),
        })

    # Losses first, then by their strongest placement.
    for key in out:
        out[key].sort(
            key=lambda p: (
                not p["beats_you"],
                p["position"] if p["position"] is not None else 999,
            ),
        )
    return out


# ── prompts ──

def _build_prompts(results) -> list[dict]:
    """Per-prompt performance: the questions the audit actually asked.

    This is the provenance behind every other number on the Overview —
    the visibility headline is just these rows aggregated. Surfacing the
    prompt text lets a reader check what was asked before trusting the
    score, which matters because the prompts are generated rather than
    taken from the user's saved library.
    """
    by_prompt: dict[str, dict] = {}

    for r in results:
        text = (r.prompt or "").strip()
        if not text:
            continue
        row = by_prompt.setdefault(text, {
            "text": text,
            "prompt_id": None,
            "runs": 0,
            "mentions": 0,
            "ranks": [],
            "sentiments": [],
            "providers": [],
        })
        # Library id, when the audited text resolves to a Prompt row. Drives
        # the deep-link to the prompt detail page; None means the row stays
        # non-clickable rather than linking somewhere broken.
        if row["prompt_id"] is None and r.source_prompt_id:
            row["prompt_id"] = str(r.source_prompt_id)
        row["runs"] += 1
        row["providers"].append({
            "name": PROVIDER_LABELS.get(r.provider, (r.provider or "").title()),
            "mentioned": bool(r.is_mentioned),
        })
        if r.is_mentioned:
            row["mentions"] += 1
            if r.mention_rank:
                row["ranks"].append(r.mention_rank)
            score = _SENTIMENT_SCORE.get(r.sentiment)
            if score is not None:
                row["sentiments"].append(score)

    rows = []
    for row in by_prompt.values():
        rows.append({
            "text": row["text"],
            "prompt_id": row["prompt_id"],
            "runs": row["runs"],
            "mentions": row["mentions"],
            "visibility": _pct(row["mentions"], row["runs"]),
            "position": round(_mean(row["ranks"]), 1) if row["ranks"] else None,
            "sentiment": round(_mean(row["sentiments"])) if row["sentiments"] else None,
            "providers": sorted(row["providers"], key=lambda p: p["name"]),
        })

    # Weakest first: a prompt you are missing from is more actionable than
    # one you already win.
    rows.sort(key=lambda r: (r["visibility"], r["text"]))
    return rows[:MAX_PROMPTS]


# ── domains ──

def _build_domains(audit_ids) -> tuple[list[dict], dict | None]:
    citations = list(
        Citation.objects.filter(audit_id__in=audit_ids).values_list(
            "apex_domain", "domain", "source_class", "reference_count",
        ),
    )
    if not citations:
        return [], None

    total = len(citations)
    retrieved: dict[str, int] = defaultdict(int)
    referenced: dict[str, int] = defaultdict(int)
    types: dict[str, str] = {}
    type_counts: dict[str, int] = defaultdict(int)

    for apex, domain, source_class, ref_count in citations:
        key = apex or domain
        if not key:
            continue
        retrieved[key] += 1
        referenced[key] += ref_count or 0
        bucket = domain_type_for(source_class)
        types[key] = bucket
        type_counts[bucket] += 1

    if not retrieved:
        return [], None

    rows = [
        {
            "domain": key,
            "retrieved": _pct(count, total),
            # Mean explicit references per retrieval, matching the
            # citation_rate definition used by the Sources dashboard.
            "citation": round(referenced[key] / count, 1) if count else 0.0,
            "type": types.get(key, "Reference"),
        }
        for key, count in sorted(retrieved.items(), key=lambda kv: -kv[1])[:MAX_DOMAINS]
    ]

    domain_types = {
        "total": _humanize(total),
        "types": [
            {
                "label": label,
                "pct": _pct(count, total),
                "color": DOMAIN_TYPE_COLORS.get(label, "var(--chart-3)"),
            }
            for label, count in sorted(type_counts.items(), key=lambda kv: -kv[1])
        ],
    }
    return rows, domain_types


# ── headline + KPI strip ──

def _build_kpis(brands: list[dict], brand_name: str) -> list[dict]:
    target = next((b for b in brands if b["is_target"]), None)
    if not target:
        return []

    cells = [
        {"label": "Visibility", "value": f"{target['visibility']:.1f}%"},
        {
            "label": "Sentiment",
            "value": "—" if target["sentiment"] is None else str(target["sentiment"]),
            "dot": True,
        },
        {
            "label": "Position",
            "value": "—" if target["position"] is None else f"#{target['position']}",
        },
        {"label": "SoV", "value": f"{target['sov']:.1f}%"},
    ]
    if target.get("trend") is not None:
        cells[0]["delta"] = f"{'+' if target['up'] else '-'}{target['trend']}%"
        cells[0]["up"] = target["up"]
    return cells


def _build_headline(brands: list[dict], brand_name: str) -> dict | None:
    """State the brand's actual standing. Never congratulate by default."""
    target = next((b for b in brands if b["is_target"]), None)
    if not target:
        return None

    rank = target["rank"]
    competitors = len(brands) - 1
    vis = target["visibility"]
    # A tie is not a lead. Only claim the top spot when strictly ahead of
    # every other measured brand.
    tied = [b for b in brands if not b["is_target"] and b["visibility"] == vis]

    if rank == 1 and not tied:
        title = "You lead on AI visibility"
        subtitle = (
            f"{brand_name} appears in {vis:.1f}% of measured answers, ahead "
            f"of {competitors} tracked competitor"
            f"{'s' if competitors != 1 else ''}."
        )
    elif tied:
        names = ", ".join(b["name"] for b in tied[:2])
        title = "You are tied on AI visibility"
        subtitle = (
            f"{brand_name} appears in {vis:.1f}% of measured answers, level "
            f"with {names}."
        )
    else:
        leader = brands[0]
        title = f"You rank #{rank} on AI visibility"
        subtitle = (
            f"{brand_name} appears in {vis:.1f}% of measured answers. "
            f"{leader['name']} currently leads at {leader['visibility']:.1f}%."
        )
    return {"title": title, "subtitle": subtitle}


# ── small helpers ──

def _pct(part: int, whole: int) -> float:
    return round((part / whole) * 100, 1) if whole else 0.0


def _mean(values) -> float:
    return sum(values) / len(values) if values else 0.0


def _humanize(n: int) -> str:
    if n >= 1000:
        return f"{n / 1000:.1f}k".replace(".0k", "k")
    return str(n)
