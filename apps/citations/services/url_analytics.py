"""Aggregation helpers for the Sources > URLs dashboard.

The dashboard surfaces, per website, how often each cited URL is *retrieved*
by the LLMs (one ``Citation`` row == one retrieval) plus derived analytics:
URL-type / domain-type classification, per-model breakdowns, movers
(Top/New/Trending/Losing), a daily retrievals time-series and a per-URL
detail view (prompts, brands, recent chats).

All counting is done in Python over a single prefetched queryset because the
per-website citation volume is modest and the derived fields (url_type,
domain_type, gap_score) are not stored on the row.

Defined metrics (documented here so the frontend/product stay in sync):

* retrievals      -- number of Citation rows for a URL in the window (the
                     page appeared as a candidate source this many times).
* citations       -- sum of reference_count: how many times the URL was
                     explicitly referenced in answer text (a subset signal of
                     retrievals).
* prompts         -- distinct prompts whose answer retrieved the URL.
* citation_rate   -- citations / retrievals, rounded to 1 dp (Peec: how often
                     a retrieved source is actually cited, averaged per use).
* gap_score       -- (distinct tracked competitors appearing in answers that
                     used the URL) x retrievals (Peec source-gap priority).
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, timedelta
from urllib.parse import urlsplit

from apps.citations.models import Citation, SourceClass

# ── source_class -> dashboard domain-type bucket ──────────────────────────
_DOMAIN_TYPE_BY_CLASS = {
    SourceClass.REDDIT: "UGC",
    SourceClass.QUORA: "UGC",
    SourceClass.STACKOVERFLOW: "UGC",
    SourceClass.FORUM: "UGC",
    SourceClass.SOCIAL: "UGC",
    SourceClass.YOUTUBE: "UGC",
    SourceClass.PODCAST: "UGC",
    SourceClass.NEWS: "Editorial",
    SourceClass.BLOG: "Editorial",
    SourceClass.WIKIPEDIA: "Reference",
    SourceClass.DOCS: "Reference",
    SourceClass.GOV: "Reference",
    SourceClass.EDU: "Reference",
    SourceClass.YOUR_SITE: "Corporate",
    SourceClass.COMPETITOR_SITE: "Corporate",
    SourceClass.OTHER: "Reference",
}

# Stable colour palette so the overview chart legend matches the frontend.
_DOMAIN_COLORS = [
    "#475569", "#8b5cf6", "#5b8def", "#ec4899", "#f59e0b",
    "#22c55e", "#06b6d4", "#f97316", "#14b8a6", "#eab308",
]
_URL_TYPE_COLORS = {
    "Listicle": "#5b8def",
    "Other": "#94a3b8",
    "Article": "#22c55e",
    "Product Page": "#8b5cf6",
    "Comparison": "#06b6d4",
    "Homepage": "#f97316",
    "How-To Guide": "#14b8a6",
    "Category Page": "#eab308",
}

# Backend provider id -> frontend model key used by SourcesUrlsPage MODELS map.
_MODEL_KEY = {
    "claude": "claude",
    "gpt4": "chatgpt",
    "gemini": "gemini",
    "perplexity": "perplexity",
    "grok": "grok",
    "deepseek": "deepseek",
    "mistral": "mistral",
    "cohere": "cohere",
    "meta_llama": "llama",
    "amazon_nova": "nova",
}


def model_key(provider: str) -> str:
    return _MODEL_KEY.get(provider, provider or "other")


def domain_type_for(source_class: str) -> str:
    return _DOMAIN_TYPE_BY_CLASS.get(source_class, "Reference")


def topic_of(result) -> str | None:
    """The dashboard "topic" for a result == the source prompt's industry name.

    This is the prompt bundle the user organises prompts under on the Prompts
    page (e.g. "ALi"). Results whose prompt text could not be linked back to a
    library Prompt have no topic.
    """
    sp = getattr(result, "source_prompt", None)
    if sp is not None and getattr(sp, "industry_id", None):
        return sp.industry.name
    return None



def classify_url_type(url: str, title: str = "") -> str:
    """Heuristic page-type classifier from the URL path + title."""
    try:
        parts = urlsplit(url)
    except ValueError:
        parts = None
    path = (parts.path if parts else "").lower()
    clean = path.strip("/")
    first_seg = clean.split("/", 1)[0] if clean else ""
    t = (title or "").lower()
    blob = f"{clean.replace('-', ' ').replace('/', ' ')} {t}"

    if not clean:
        return "Homepage"
    if any(k in blob for k in (" vs ", "vs.", "compare", "comparison", "versus")):
        return "Comparison"
    if "how to" in blob or "how-to" in path:
        return "How-To Guide"
    # "10 best", "top 7", "5 apps" — leading-number listicles.
    if first_seg[:2].strip("-").isdigit() or t.split(" ", 1)[0].isdigit() or any(
        k in blob for k in ("best ", "top ", " best", " top ")
    ):
        return "Listicle"
    if any(k in path for k in ("/category", "/categories", "/topics", "/tag/")):
        return "Category Page"
    if any(k in path for k in ("/product", "/pricing", "/features")):
        return "Product Page"
    if any(k in path for k in ("/blog", "/article", "/news", "/post")):
        return "Article"
    return "Other"


def _prev_window(start: date, end: date) -> tuple[date, date]:
    span = (end - start).days or 1
    return start - timedelta(days=span), start - timedelta(days=1)


def tracked_competitors(website) -> set[str]:
    """Lower-cased names of the website's tracked competitors."""
    out: set[str] = set()
    for comp in (getattr(website, "competitors", None) or []):
        if isinstance(comp, dict):
            name = (comp.get("name") or "").strip().lower()
        else:
            name = str(comp).strip().lower()
        if name:
            out.add(name)
    return out


def _aggregate_rows(citations, competitors: set[str] | None = None) -> dict[str, dict]:
    """Group citations by normalized_url into per-URL accumulators.

    ``competitors`` is the set of tracked competitor names (lower-cased) used
    to compute the gap score.
    """
    competitors = competitors or set()
    by_url: dict[str, dict] = {}
    for c in citations:
        key = c.normalized_url or c.url
        agg = by_url.get(key)
        if agg is None:
            agg = by_url[key] = {
                "normalized_url": key,
                "url": c.url,
                "title": c.title or "",
                "domain": c.domain,
                "apex_domain": c.apex_domain,
                "source_class": c.source_class,
                "retrievals": 0,
                "references": 0,
                "prompts": set(),
                "providers": set(),
                "positions": [],
                "competitors": set(),
                "is_target": False,
                "is_competitor": False,
                "first_seen": c.created_at,
                "last_seen": c.created_at,
            }
        agg["retrievals"] += 1
        agg["references"] += getattr(c, "reference_count", 0) or 0
        if not agg["title"] and c.title:
            agg["title"] = c.title
        result = c.result
        agg["prompts"].add((result.prompt_index, result.prompt))
        agg["providers"].add(result.provider)
        if c.position is not None:
            agg["positions"].append(c.position)
        agg["is_target"] = agg["is_target"] or c.is_target
        agg["is_competitor"] = agg["is_competitor"] or c.is_competitor
        if c.created_at < agg["first_seen"]:
            agg["first_seen"] = c.created_at
        if c.created_at > agg["last_seen"]:
            agg["last_seen"] = c.created_at
        # Gap: which tracked competitors appear in answers that used this URL.
        for comp in (result.competitors_mentioned or []):
            name = (comp.get("name") if isinstance(comp, dict) else str(comp)) or ""
            name = name.strip().lower()
            if name and name in competitors:
                agg["competitors"].add(name)
    return by_url


def _row_payload(agg: dict) -> dict:
    retrievals = agg["retrievals"]
    references = agg["references"]
    # Citation rate (Peec): how often a retrieved source is actually
    # referenced in the answer text, averaged over retrievals.
    citation_rate = round(references / retrievals, 1) if retrievals else 0.0
    # Gap score (Peec): tracked competitors present in the source x usage.
    gap_score = len(agg["competitors"]) * retrievals
    parts = urlsplit(agg["url"])
    path = f"{parts.netloc}{parts.path}".rstrip("/")
    return {
        "url": agg["url"],
        "normalized_url": agg["normalized_url"],
        "title": agg["title"] or agg["apex_domain"],
        "path": path or agg["apex_domain"],
        "domain": agg["domain"],
        "apex_domain": agg["apex_domain"],
        "url_type": classify_url_type(agg["url"], agg["title"]),
        "domain_type": domain_type_for(agg["source_class"]),
        "source_class": agg["source_class"],
        "models": sorted({model_key(p) for p in agg["providers"]}),
        "retrievals": retrievals,
        "citations": references,
        "prompts": len(agg["prompts"]),
        "citation_rate": citation_rate,
        "gap_score": gap_score,
        "is_target": agg["is_target"],
        "is_competitor": agg["is_competitor"],
        "first_seen": agg["first_seen"].isoformat(),
        "last_seen": agg["last_seen"].isoformat(),
    }


def build_urls_overview(website, *, start: date, end: date, provider: str | None = None,
                        topic: str | None = None) -> dict:
    """Full payload for the URLs list view, optionally scoped to one topic."""
    qs = (
        Citation.objects.filter(
            audit__website=website,
            created_at__date__gte=start,
            created_at__date__lte=end,
        )
        .select_related("result", "result__source_prompt__industry")
    )
    if provider:
        qs = qs.filter(result__provider=provider)
    citations = list(qs)

    # Topics dropdown reflects every topic in the (period + provider) scope,
    # regardless of the currently selected topic, so the user can switch.
    topic_counter: Counter = Counter()
    for c in citations:
        t = topic_of(c.result)
        if t:
            topic_counter[t] += 1
    topics = [
        {"name": name, "count": count}
        for name, count in topic_counter.most_common()
    ]

    if topic:
        citations = [c for c in citations if topic_of(c.result) == topic]

    by_url = _aggregate_rows(citations, tracked_competitors(website))
    rows = [_row_payload(a) for a in by_url.values()]
    rows.sort(key=lambda r: r["retrievals"], reverse=True)

    total_retrievals = sum(r["retrievals"] for r in rows)

    # ── URL types breakdown ──
    type_counter: Counter = Counter()
    for r in rows:
        type_counter[r["url_type"]] += r["retrievals"]
    url_types = [
        {
            "type": t,
            "count": c,
            "pct": round(100 * c / total_retrievals) if total_retrievals else 0,
            "color": _URL_TYPE_COLORS.get(t, "#94a3b8"),
        }
        for t, c in type_counter.most_common()
    ]

    # ── Overview time-series: daily retrievals for the top domains ──
    days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    domain_totals: Counter = Counter()
    domain_daily: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for c in citations:
        apex = c.apex_domain or c.domain
        if not apex:
            continue
        domain_totals[apex] += 1
        domain_daily[apex][c.created_at.date().isoformat()] += 1
    top_domains = [d for d, _ in domain_totals.most_common(5)]
    series = [
        {
            "key": d,
            "label": d,
            "color": _DOMAIN_COLORS[i % len(_DOMAIN_COLORS)],
            "data": [domain_daily[d].get(day.isoformat(), 0) for day in days],
        }
        for i, d in enumerate(top_domains)
    ]
    overview = {
        "labels": [day.strftime("%b %d") for day in days],
        "series": series,
    }

    # ── Movers ──
    movers = _build_movers(citations, rows, start, end)

    return {
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "total_retrievals": total_retrievals,
        "unique_urls": len(rows),
        "topics": topics,
        "selected_topic": topic or None,
        "overview": overview,
        "movers": movers,
        "url_types": url_types,
        "urls": rows,
    }


def _build_movers(citations, rows, start: date, end: date) -> dict:
    mid = start + timedelta(days=((end - start).days + 1) // 2)
    recent_cut = end - timedelta(days=min(7, max(1, (end - start).days // 4)))

    first_seen: dict[str, date] = {}
    recent: Counter = Counter()
    prior: Counter = Counter()
    title_by_url: dict[str, str] = {}
    for c in citations:
        key = c.normalized_url or c.url
        d = c.created_at.date()
        if key not in first_seen or d < first_seen[key]:
            first_seen[key] = d
        if c.title and key not in title_by_url:
            title_by_url[key] = c.title
        if d >= mid:
            recent[key] += 1
        else:
            prior[key] += 1

    by_key = {r["normalized_url"]: r for r in rows}

    def entry(key):
        r = by_key.get(key, {})
        return {
            "url": r.get("url", key),
            "title": r.get("title") or title_by_url.get(key) or key,
            "retrievals": r.get("retrievals", 0),
        }

    top = [entry(r["normalized_url"]) for r in rows[:8]]

    new = sorted(
        (k for k, fs in first_seen.items() if fs >= recent_cut),
        key=lambda k: by_key.get(k, {}).get("retrievals", 0),
        reverse=True,
    )
    new_rows = [entry(k) for k in new[:8]]

    deltas = {k: recent[k] - prior[k] for k in set(recent) | set(prior)}
    trending = sorted(
        (k for k, dlt in deltas.items() if dlt > 0), key=lambda k: deltas[k], reverse=True
    )
    losing = sorted(
        (k for k, dlt in deltas.items() if dlt < 0), key=lambda k: deltas[k]
    )

    def with_delta(keys):
        out = []
        for k in keys[:8]:
            e = entry(k)
            e["delta"] = deltas.get(k, 0)
            out.append(e)
        return out

    return {
        "Top": top,
        "New": new_rows,
        "Trending": with_delta(trending),
        "Losing": with_delta(losing),
    }


def build_url_detail(website, *, normalized_url: str, start: date, end: date,
                     provider: str | None = None, topic: str | None = None) -> dict | None:
    """Detail payload for a single cited URL. Returns None if not found."""
    prev_start, prev_end = _prev_window(start, end)

    qs = (
        Citation.objects.filter(
            audit__website=website,
            normalized_url=normalized_url,
            created_at__date__gte=prev_start,
            created_at__date__lte=end,
        )
        .select_related("result", "result__source_prompt__industry")
    )
    if provider:
        qs = qs.filter(result__provider=provider)
    citations = list(qs)
    if topic:
        citations = [c for c in citations if topic_of(c.result) == topic]
    if not citations:
        return None

    current = [c for c in citations if c.created_at.date() >= start]
    previous = [c for c in citations if c.created_at.date() < start]
    if not current:
        current = citations  # fall back so the page still renders

    sample = current[0]
    agg = _aggregate_rows(current, tracked_competitors(website))
    row = _row_payload(next(iter(agg.values())))

    cur_retr = len(current)
    prev_retr = len(previous)
    cur_prompts = len({(c.result.prompt_index, c.result.prompt) for c in current})
    prev_prompts = len({(c.result.prompt_index, c.result.prompt) for c in previous})
    cur_refs = sum(getattr(c, "reference_count", 0) or 0 for c in current)
    prev_refs = sum(getattr(c, "reference_count", 0) or 0 for c in previous)
    cur_rate = round(cur_refs / cur_retr, 1) if cur_retr else 0.0
    prev_rate = round(prev_refs / prev_retr, 1) if prev_retr else 0.0
    first_seen = min(c.created_at for c in citations)
    last_seen = max(c.created_at for c in citations)

    metrics = {
        "url": sample.url,
        "title": row["title"],
        "url_type": row["url_type"],
        "domain_type": row["domain_type"],
        "retrievals": {"value": cur_retr, "delta": cur_retr - prev_retr},
        "citation_rate": {"value": cur_rate, "delta": round(cur_rate - prev_rate, 1)},
        "prompts": {"value": cur_prompts, "delta": cur_prompts - prev_prompts},
        "first_seen": first_seen.isoformat(),
        "last_seen": last_seen.isoformat(),
    }

    # ── Retrievals over time (current vs previous period) ──
    days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    cur_daily: Counter = Counter(c.created_at.date().isoformat() for c in current)
    prev_daily: Counter = Counter(c.created_at.date().isoformat() for c in previous)
    prev_days = [prev_start + timedelta(days=i) for i in range((prev_end - prev_start).days + 1)]
    retrievals_over_time = {
        "labels": [d.strftime("%b %d") for d in days],
        "current": [cur_daily.get(d.isoformat(), 0) for d in days],
        "previous": [prev_daily.get(d.isoformat(), 0) for d in prev_days],
    }

    # ── Retrievals by model ──
    cur_by_model: Counter = Counter(model_key(c.result.provider) for c in current)
    prev_by_model: Counter = Counter(model_key(c.result.provider) for c in previous)
    models = sorted(set(cur_by_model) | set(prev_by_model))
    retrievals_by_model = [
        {
            "model": m,
            "current": cur_by_model.get(m, 0),
            "previous": prev_by_model.get(m, 0),
        }
        for m in models
    ]

    # ── Prompts table ──
    prompt_acc: dict[str, dict] = {}
    for c in current:
        r = c.result
        p = prompt_acc.setdefault(r.prompt, {
            "prompt": r.prompt,
            "topic": topic_of(r) or r.get_prompt_type_display(),
            "retrieved": 0,
            "references": 0,
        })
        p["retrieved"] += 1
        p["references"] += getattr(c, "reference_count", 0) or 0
    prompts_table = []
    for p in sorted(prompt_acc.values(), key=lambda x: x["retrieved"], reverse=True):
        prompts_table.append({
            "prompt": p["prompt"],
            "topic": p["topic"],
            "retrieved": p["retrieved"],
            "citation_rate": round(p["references"] / p["retrieved"], 1) if p["retrieved"] else 0.0,
        })

    # ── Brands mentioned (target + competitors across the citing answers) ──
    brand_freq: Counter = Counter()
    brand_pos: dict[str, list[int]] = defaultdict(list)
    brand_name = website.name
    for c in current:
        r = c.result
        if r.is_mentioned:
            brand_freq[brand_name] += 1
            if r.mention_rank:
                brand_pos[brand_name].append(r.mention_rank)
        for comp in (r.competitors_mentioned or []):
            name = (comp.get("name") or "").strip() if isinstance(comp, dict) else str(comp)
            if not name:
                continue
            brand_freq[name] += 1
            pos = comp.get("position") if isinstance(comp, dict) else None
            if pos:
                brand_pos[name].append(pos)
    brands_mentioned = []
    for name, freq in brand_freq.most_common():
        positions = brand_pos.get(name) or []
        brands_mentioned.append({
            "brand": name,
            "position": min(positions) if positions else None,
            "frequency": freq,
        })
    brands_mentioned.sort(key=lambda b: (b["position"] is None, b["position"] or 0))

    # ── Recent chats ──
    chats = []
    seen_results = set()
    for c in sorted(current, key=lambda c: c.created_at, reverse=True):
        r = c.result
        if r.id in seen_results:
            continue
        seen_results.add(r.id)
        other_sources = [
            oc.apex_domain for oc in current
            if oc.result_id == r.id and oc.normalized_url != normalized_url
        ]
        chats.append({
            "result_id": str(r.id),
            "prompt": r.prompt,
            "response_preview": (r.response_text or "")[:180],
            "brand_mentioned": r.is_mentioned,
            "models": [model_key(r.provider)],
            "sources": sorted(set(s for s in other_sources if s))[:6],
            "position": c.position,
            "created_at": r.created_at.isoformat(),
        })
        if len(chats) >= 20:
            break

    return {
        "metrics": metrics,
        "retrievals_over_time": retrievals_over_time,
        "retrievals_by_model": retrievals_by_model,
        "prompts": prompts_table,
        "brands_mentioned": brands_mentioned,
        "chats": chats,
    }
