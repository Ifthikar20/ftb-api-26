"""Turn the URLs dashboard into actions.

Three rule-based buckets computed from the already-enriched /urls/ rows
(run AFTER traffic_enrichment so ``gsc`` and ``ai_visits`` are present):

* ``seo_gap``     — your pages that AI already cites but Google buries
                    (proven-with-AI content whose SEO is the bottleneck).
* ``content_gap`` — third-party or competitor pages that feed answers
                    where your tracked competitors appear (the pages to
                    match with comparable content of your own).
* ``winning``     — your pages that AI cites AND that earn real visits
                    (the topics to double down on).

Pure functions over the payload rows: no queries, no storage. Buckets are
capped so the section reads as a to-do list, not another table.
"""
from __future__ import annotations

MAX_ITEMS_PER_BUCKET = 5

# Google position beyond which a page is effectively invisible in search
# (page two or worse).
_BURIED_POSITION = 10.0


def _base_item(row: dict) -> dict:
    return {
        "url": row.get("url", ""),
        "normalized_url": row.get("normalized_url", ""),
        "title": row.get("title") or row.get("apex_domain", ""),
        "retrievals": row.get("retrievals", 0),
    }


def _seo_gap(rows: list[dict], *, gsc_ready: bool) -> list[dict]:
    if not gsc_ready:
        return []
    items = []
    for row in rows:
        if row.get("source_class") != "your_site" or not row.get("citations"):
            continue
        gsc = row.get("gsc")
        position = (gsc or {}).get("position")
        buried = position is not None and position > _BURIED_POSITION
        invisible = gsc is None or not (gsc or {}).get("impressions")
        if not (buried or invisible):
            continue
        item = _base_item(row)
        item["gsc_position"] = position
        if buried:
            item["reason"] = (
                f"Cited {row['citations']} time(s) by AI but ranks "
                f"#{position:.0f} on Google"
            )
        else:
            item["reason"] = (
                f"Cited {row['citations']} time(s) by AI but gets no "
                f"Google impressions"
            )
        item["action"] = "Improve SEO on this page"
        items.append(item)
    items.sort(key=lambda i: i["retrievals"], reverse=True)
    return items[:MAX_ITEMS_PER_BUCKET]


def _content_gap(rows: list[dict]) -> list[dict]:
    items = []
    for row in rows:
        if row.get("source_class") == "your_site":
            continue
        if not row.get("gap_score") or row.get("retrievals", 0) < 2:
            continue
        names = row.get("competitor_names") or []
        shown = ", ".join(n.title() for n in names[:3])
        item = _base_item(row)
        item["gap_score"] = row["gap_score"]
        item["competitor_names"] = names
        item["reason"] = (
            f"Used {row['retrievals']} time(s) in answers that feature {shown}"
            if shown else
            f"Used {row['retrievals']} time(s) in answers featuring your competitors"
        )
        item["action"] = "Create a comparable page"
        items.append(item)
    items.sort(key=lambda i: i["gap_score"], reverse=True)
    return items[:MAX_ITEMS_PER_BUCKET]


def _winning(rows: list[dict]) -> list[dict]:
    items = []
    for row in rows:
        if row.get("source_class") != "your_site" or not row.get("citations"):
            continue
        clicks = (row.get("gsc") or {}).get("clicks") or 0
        ai_visits = row.get("ai_visits") or 0
        if not clicks and not ai_visits:
            continue
        parts = []
        if clicks:
            parts.append(f"{clicks} Google click(s)")
        if ai_visits:
            parts.append(f"{ai_visits} AI-referred visit(s)")
        item = _base_item(row)
        item["clicks"] = clicks
        item["ai_visits"] = ai_visits
        item["reason"] = f"Cited by AI and earning {' and '.join(parts)}"
        item["action"] = "Double down on this topic"
        items.append(item)
    items.sort(key=lambda i: i["retrievals"], reverse=True)
    return items[:MAX_ITEMS_PER_BUCKET]


def build_opportunities(payload: dict) -> dict:
    """Compute the opportunities block from an enriched /urls/ payload."""
    rows = payload.get("urls") or []
    summary = payload.get("traffic_summary") or {}
    gsc_ready = bool(summary.get("gsc_connected") and summary.get("gsc_has_data"))
    pixel_ready = bool(summary.get("pixel_active"))

    return {
        "available": {"gsc": gsc_ready, "pixel": pixel_ready},
        "buckets": [
            {
                "key": "seo_gap",
                "title": "AI cites you, Google buries you",
                "items": _seo_gap(rows, gsc_ready=gsc_ready),
            },
            {
                "key": "content_gap",
                "title": "AI answers skip your brand",
                "items": _content_gap(rows),
            },
            {
                "key": "winning",
                "title": "Working well",
                "items": _winning(rows),
            },
        ],
    }
