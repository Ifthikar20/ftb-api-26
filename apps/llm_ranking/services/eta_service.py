"""
ETA estimation for LLM ranking audits.

Two flavours:

  • ``estimate_audit_duration(website)`` — look at the last N completed
    audits for this website, return the median per-cell duration. Used
    to project how long a *running* audit has left or how long the
    *next scheduled* audit will take.

  • ``schedule_eta(schedule)`` — wraps the above with the schedule's
    next_run_at, projected query count, and whether the schedule is
    currently in-flight.

Median, not mean — a single 90-second outlier on a flaky API key
would otherwise drag the projection up and demoralize the user.
"""
from __future__ import annotations

import statistics

from django.utils import timezone

# Fallback when there's no history yet. Empirically, a healthy 4-provider
# / 10-prompt audit completes in ~30s when keys are valid. Under hash-
# fallback embeddings or 401-storming, this drops; either way, a 1.5s
# baseline per cell is a safe over-estimate that won't underpromise.
_FALLBACK_PER_CELL_SECONDS = 1.5
_HISTORY_WINDOW = 8


def estimate_audit_duration(
    website,
    *,
    n_prompts: int,
    n_providers: int,
) -> float:
    """
    Return a projected total duration in seconds for an audit covering
    ``n_prompts × n_providers`` cells against this website.

    Uses the median per-cell duration from the last 8 completed audits
    on this website. Falls back to a 1.5s constant when no history.
    """
    from apps.llm_ranking.models import LLMRankingAudit

    cells = max(1, n_prompts * n_providers)
    history = (
        LLMRankingAudit.objects
        .filter(
            website=website,
            status=LLMRankingAudit.STATUS_COMPLETED,
            duration_seconds__isnull=False,
            total_queries__gt=0,
        )
        .order_by("-completed_at")
        .values_list("duration_seconds", "total_queries")[:_HISTORY_WINDOW]
    )
    per_cell = [
        float(d) / int(q)
        for d, q in history
        if d and q and float(d) > 0 and int(q) > 0
    ]
    if not per_cell:
        return cells * _FALLBACK_PER_CELL_SECONDS
    return cells * statistics.median(per_cell)


def schedule_eta(schedule) -> dict:
    """
    Build the ETA payload for a schedule's next dispatch.

    Returns a dict with:
      - next_run_at        ISO-8601 of the next dispatch
      - seconds_until_run  delta from now to next_run_at (negative if past)
      - n_prompts          projected prompt count
      - n_providers        configured provider count
      - estimated_duration_seconds   median-based projection
      - in_flight          true if last_audit is still running
      - in_flight_audit_id last audit's UUID when in_flight
      - in_flight_progress {completed, total} when in_flight
    """
    from django.conf import settings as dj_settings

    from apps.llm_ranking.models import LLMRankingAudit
    from apps.llm_ranking.providers import PROVIDERS as PROV_REGISTRY

    n_prompts = _projected_prompt_count(schedule)
    requested = schedule.providers or list(PROV_REGISTRY.keys())
    n_providers = max(1, sum(
        1 for k in requested
        if k in PROV_REGISTRY
        and getattr(dj_settings, PROV_REGISTRY[k].api_key_setting, "")
    ))

    duration = estimate_audit_duration(
        schedule.website, n_prompts=n_prompts, n_providers=n_providers,
    )

    now = timezone.now()
    seconds_until_run = (
        (schedule.next_run_at - now).total_seconds()
        if schedule.next_run_at else None
    )

    payload: dict = {
        "next_run_at": schedule.next_run_at.isoformat() if schedule.next_run_at else None,
        "seconds_until_run": seconds_until_run,
        "n_prompts": n_prompts,
        "n_providers": n_providers,
        "estimated_duration_seconds": round(duration, 1),
        "in_flight": False,
        "in_flight_audit_id": None,
        "in_flight_progress": None,
        "consecutive_failures": schedule.consecutive_failures or 0,
        "is_paused": not schedule.is_enabled,
    }

    prev = schedule.last_audit
    if prev and prev.status in (
        LLMRankingAudit.STATUS_PENDING, LLMRankingAudit.STATUS_RUNNING,
    ):
        payload["in_flight"] = True
        payload["in_flight_audit_id"] = str(prev.id)
        payload["in_flight_progress"] = {
            "completed": prev.queries_completed or 0,
            "total": prev.total_queries or 0,
        }
        # When a run is in flight, surface its remaining-time estimate too.
        cells_left = max(0, (prev.total_queries or 0) - (prev.queries_completed or 0))
        if cells_left and prev.total_queries:
            per_cell = duration / max(1, n_prompts * n_providers)
            payload["in_flight_seconds_remaining"] = round(cells_left * per_cell, 1)

    return payload


def _projected_prompt_count(schedule) -> int:
    """Estimate how many prompts the next audit will produce. Mirrors
    ``LLMRankingService.generate_prompts`` capping logic without
    actually invoking it (which would hit Claude)."""
    try:
        from core.utils.constants import max_prompts_for_user
        cap = max_prompts_for_user(schedule.created_by or schedule.website.user)
    except Exception:
        cap = 10
    return max(1, min(cap, 10))


def format_eta(seconds: float | None) -> str:
    """Human-friendly ETA string. Used by the UI label fallback."""
    if seconds is None:
        return "—"
    s = int(round(seconds))
    if s < 0:
        return "any moment"
    if s < 90:
        return f"in {s}s"
    if s < 3600:
        return f"in {s // 60}m"
    if s < 86400:
        return f"in {s // 3600}h"
    days = s // 86400
    return f"in {days}d"
