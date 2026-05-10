import logging
from datetime import timedelta

from celery import chord, shared_task

logger = logging.getLogger("apps")


@shared_task(name="apps.llm_ranking.tasks.run_llm_ranking_audit", bind=True, max_retries=1)
def run_llm_ranking_audit(self, *, audit_id: str) -> None:
    """
    Run a full LLM ranking audit asynchronously.

    Uses a Celery chord to fan out one task per (prompt, provider) cell so:
      - cells run in parallel up to worker concurrency
      - a single cell failure doesn't kill the whole audit
      - retries are bounded per cell, not per audit
      - workers can restart mid-audit without losing committed cells

    The aggregator task is the chord callback — it computes scores once
    every cell has either committed a row or hit max retries.
    """
    from apps.llm_ranking.models import LLMRankingAudit
    from apps.llm_ranking.services.ranking_service import LLMRankingService

    try:
        # Synchronous prep: enrichment + status flip + persist context.
        # Fast (a few HTTP calls); doing it inside the chord adds no value.
        plan = LLMRankingService.prepare_audit(audit_id=audit_id)
        if not plan:
            return  # already terminal or non-existent

        cells = [
            query_provider_prompt_task.s(
                audit_id=audit_id,
                prompt_index=p_idx,
                provider=provider,
            )
            for p_idx in range(len(plan["prompts"]))
            for provider in plan["providers"]
        ]
        if not cells:
            # No work to do — flip to completed with an empty score.
            aggregate_audit_results_task.delay([], audit_id=audit_id)
            return

        chord(cells)(aggregate_audit_results_task.s(audit_id=audit_id))
    except Exception as exc:
        logger.error("LLM ranking audit %s failed: %s", audit_id, exc)
        try:
            LLMRankingAudit.objects.filter(id=audit_id).update(
                status=LLMRankingAudit.STATUS_FAILED,
                error_message=str(exc)[:500],
            )
        except Exception:
            pass
        raise self.retry(exc=exc, countdown=30) from None


@shared_task(
    name="apps.llm_ranking.tasks.query_provider_prompt",
    bind=True, max_retries=2, default_retry_delay=10, acks_late=True,
)
def query_provider_prompt_task(self, *, audit_id: str, prompt_index: int, provider: str) -> dict:
    """
    Run one (prompt, provider) cell of an audit. Idempotent: a duplicate run
    of the same (audit, prompt_index, provider, run_id=0) tuple updates the
    existing row instead of creating a second one. Errors do not propagate
    to the chord — we always commit a row so aggregation can proceed.
    """
    from apps.llm_ranking.services.ranking_service import LLMRankingService
    try:
        return LLMRankingService.run_audit_cell(
            audit_id=audit_id, prompt_index=prompt_index, provider=provider,
        )
    except Exception as exc:
        # Log but don't kill the chord — return a sentinel so aggregation
        # still runs. Retry once on transient errors via Celery's retry.
        logger.warning(
            "Audit %s cell (%d/%s) failed: %s", audit_id, prompt_index, provider, exc,
        )
        try:
            self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            return {"audit_id": audit_id, "prompt_index": prompt_index,
                    "provider": provider, "error": str(exc)[:200]}


@shared_task(name="apps.llm_ranking.tasks.aggregate_audit_results")
def aggregate_audit_results_task(_cell_results, *, audit_id: str) -> None:
    """
    Chord callback — compute aggregate scores and roll up cost once every
    cell has committed (or exhausted retries). Receives the list of cell
    return values; we ignore them and re-read from the DB for consistency.
    """
    from apps.llm_ranking.services.ranking_service import LLMRankingService
    LLMRankingService.finalise_audit(audit_id=audit_id)


# ── Periodic scheduling ─────────────────────────────────────────────────────


FREQUENCY_DELTAS = {
    "weekly": timedelta(weeks=1),
    "biweekly": timedelta(weeks=2),
    "monthly": timedelta(days=30),
}


@shared_task(name="apps.llm_ranking.tasks.dispatch_scheduled_audits")
def dispatch_scheduled_audits() -> None:
    """
    Celery Beat task: check all enabled LLMRankingSchedule records
    whose ``next_run_at`` has passed, create an audit, and advance
    the schedule.

    Runs every 15 minutes via ``beat_schedule``.

    Resilience guarantees:
      • If the previous audit is still pending/running, do NOT enqueue
        a second one — just bump ``next_run_at`` so we re-check next
        cycle. Avoids stacking duplicates when a slow audit overruns
        its cadence.
      • Track ``consecutive_failures`` and auto-pause the schedule
        once it crosses ``auto_pause_threshold``. Operator can re-
        enable explicitly.
      • Per-user monthly AI spend cap is checked first — skip + advance
        rather than burn credits while the cap is held.
    """
    from django.utils import timezone

    from apps.llm_ranking.models import LLMRankingAudit, LLMRankingSchedule
    from apps.llm_ranking.services.ranking_service import LLMRankingService

    now = timezone.now()
    due = LLMRankingSchedule.objects.filter(
        is_enabled=True,
        next_run_at__lte=now,
    ).select_related("website", "last_audit")

    for schedule in due:
        try:
            cap_user = schedule.created_by

            # ── 1. Skip if previous run still in flight ──────────────
            prev = schedule.last_audit
            if prev and prev.status in (
                LLMRankingAudit.STATUS_PENDING,
                LLMRankingAudit.STATUS_RUNNING,
            ):
                logger.info(
                    "Skipping scheduled audit for %s: previous audit %s "
                    "still %s.", schedule.website.name, prev.id, prev.status,
                )
                _bump_next_run(schedule, now)
                continue

            # ── 2. Spend-cap check ────────────────────────────────────
            cap = float(getattr(cap_user, "monthly_ai_cost_cap_usd", 0) or 0)
            if cap > 0:
                from core.ai_tracking import month_to_date_cost
                spent = month_to_date_cost(cap_user)
                if spent >= cap:
                    logger.warning(
                        "Skipping scheduled audit for %s: user %s at cap "
                        "($%.2f / $%.2f).",
                        schedule.website.name, cap_user.id, spent, cap,
                    )
                    _bump_next_run(schedule, now)
                    continue

            # ── 3. Generate + filter providers ────────────────────────
            prompts = LLMRankingService.generate_prompts(
                business_name=schedule.business_name,
                industry=schedule.industry,
                description=schedule.business_description,
                keywords=schedule.keywords,
                location=schedule.location,
                user=cap_user,
                website=schedule.website,
            )
            from apps.llm_ranking.providers import PROVIDERS
            from django.conf import settings as _settings
            requested = schedule.providers or list(PROVIDERS.keys())
            selected_providers = [
                key for key in requested
                if key in PROVIDERS
                and getattr(_settings, PROVIDERS[key].api_key_setting, "")
            ] or ["claude"]

            audit = LLMRankingAudit.objects.create(
                website=schedule.website,
                created_by=schedule.created_by,
                business_name=schedule.business_name,
                business_description=schedule.business_description,
                industry=schedule.industry,
                location=schedule.location,
                keywords=schedule.keywords,
                prompts=prompts,
                providers_queried=selected_providers,
            )

            # Queue execution + record the audit on the schedule so the
            # next dispatch cycle can detect it's still in flight.
            run_llm_ranking_audit.delay(audit_id=str(audit.id))

            # Advance + reset failure counter (success path).
            delta = FREQUENCY_DELTAS.get(schedule.frequency, timedelta(weeks=1))
            schedule.last_run_at = now
            schedule.next_run_at = now + delta
            schedule.last_audit = audit
            schedule.consecutive_failures = 0
            schedule.last_failure_at = None
            schedule.save(update_fields=[
                "last_run_at", "next_run_at", "last_audit",
                "consecutive_failures", "last_failure_at", "updated_at",
            ])

            logger.info(
                "Scheduled LLM audit created for %s (schedule=%s, next=%s)",
                schedule.website.name, schedule.id, schedule.next_run_at,
            )

        except Exception as exc:
            logger.error(
                "Failed to dispatch scheduled LLM audit for schedule %s: %s",
                schedule.id, exc,
            )
            _record_failure(schedule, now)


def _bump_next_run(schedule, now) -> None:
    """Advance next_run_at without recording success or failure."""
    delta = FREQUENCY_DELTAS.get(schedule.frequency, timedelta(weeks=1))
    schedule.next_run_at = now + delta
    schedule.save(update_fields=["next_run_at", "updated_at"])


def _record_failure(schedule, now) -> None:
    """
    Increment ``consecutive_failures``; auto-pause the schedule when
    the counter crosses ``auto_pause_threshold``. Always advance
    ``next_run_at`` so a transient error doesn't tight-loop the
    dispatcher.
    """
    schedule.consecutive_failures = (schedule.consecutive_failures or 0) + 1
    schedule.last_failure_at = now
    delta = FREQUENCY_DELTAS.get(schedule.frequency, timedelta(weeks=1))
    schedule.next_run_at = now + delta
    update_fields = [
        "consecutive_failures", "last_failure_at",
        "next_run_at", "updated_at",
    ]
    if schedule.consecutive_failures >= (schedule.auto_pause_threshold or 3):
        schedule.is_enabled = False
        update_fields.append("is_enabled")
        logger.warning(
            "Auto-pausing schedule %s after %d consecutive failures.",
            schedule.id, schedule.consecutive_failures,
        )
    schedule.save(update_fields=update_fields)


# ── Model Test (standalone probe) ─────────────────────────────────
# Stored in Redis under MODEL_TEST_CACHE_KEY.format(run_id=...). The
# value is a dict the polling endpoint serves verbatim:
#   { status, prompts, providers, brand_terms, completed, total,
#     current_prompt, current_provider, results, summary, error }
MODEL_TEST_CACHE_KEY = "model_test:run:{run_id}"
MODEL_TEST_TTL_SECONDS = 60 * 60  # 1h — plenty for poll-and-leave UX

def _model_test_state_get(run_id: str) -> dict | None:
    from django.core.cache import cache
    return cache.get(MODEL_TEST_CACHE_KEY.format(run_id=run_id))

def _model_test_state_set(run_id: str, state: dict) -> None:
    from django.core.cache import cache
    cache.set(
        MODEL_TEST_CACHE_KEY.format(run_id=run_id),
        state,
        timeout=MODEL_TEST_TTL_SECONDS,
    )


@shared_task(name="apps.llm_ranking.tasks.run_model_test", bind=True, max_retries=0)
def run_model_test(self, *, run_id: str, website_id: str, user_id: int | None,
                   prompts: list[str], providers: list[str],
                   brand_terms: list[str]) -> None:
    """
    Background worker for the Model Test probe. Updates Redis state
    after each (prompt, provider) call so the FE can poll and render
    results as they arrive.
    """
    from django.contrib.auth import get_user_model
    from apps.llm_ranking.providers import get_provider
    from apps.websites.models import Website

    state = _model_test_state_get(run_id) or {}
    state.update({
        "status": "running",
        "prompts": prompts,
        "providers": providers,
        "brand_terms": brand_terms,
        "total": len(prompts) * len(providers),
        "completed": 0,
        "current_prompt_index": 0,
        "current_provider": providers[0] if providers else "",
        "results": [],
        "summary": None,
        "error": None,
    })
    _model_test_state_set(run_id, state)

    try:
        website = Website.objects.filter(id=website_id).first()
        user = None
        if user_id is not None:
            user = get_user_model().objects.filter(id=user_id).first()

        terms_lower = [t.lower() for t in brand_terms if t]

        def _hit(text: str) -> bool:
            if not text or not terms_lower:
                return False
            low = text.lower()
            return any(t in low for t in terms_lower)

        for p_idx, prompt_text in enumerate(prompts):
            row = {"prompt": prompt_text, "responses": []}
            state["current_prompt_index"] = p_idx
            for key in providers:
                state["current_provider"] = key
                _model_test_state_set(run_id, state)

                provider = get_provider(key)
                if provider is None or not provider.is_configured():
                    row["responses"].append({
                        "provider": key, "succeeded": False,
                        "error": "Provider not configured (missing API key).",
                        "response_text": "", "brand_mentioned": False,
                        "duration_ms": 0,
                    })
                else:
                    try:
                        pr = provider.query(
                            prompt_text, user=user, website=website,
                            audit_id="model_test", role="upstream",
                        )
                        row["responses"].append({
                            "provider": key,
                            "succeeded": bool(pr.succeeded),
                            "error": getattr(pr, "error", "") or "",
                            "response_text": getattr(pr, "text", "") or "",
                            "brand_mentioned": _hit(getattr(pr, "text", "") or ""),
                            "duration_ms": getattr(pr, "duration_ms", 0) or 0,
                        })
                    except Exception as exc:
                        logger.warning("model_test %s/%s failed: %s", run_id, key, exc)
                        row["responses"].append({
                            "provider": key, "succeeded": False,
                            "error": str(exc)[:300],
                            "response_text": "", "brand_mentioned": False,
                            "duration_ms": 0,
                        })

                state["completed"] = state.get("completed", 0) + 1
                _model_test_state_set(run_id, state)

            state["results"].append(row)
            _model_test_state_set(run_id, state)

        # Final summary
        results = state["results"]
        prompts_with_hit = sum(
            1 for r in results if any(x["brand_mentioned"] for x in r["responses"])
        )
        hits = sum(1 for r in results for x in r["responses"] if x["brand_mentioned"])
        state["summary"] = {
            "prompts": len(prompts),
            "providers": providers,
            "total_runs": state["total"],
            "hits": hits,
            "prompts_with_hit": prompts_with_hit,
            "discovery_rate": round(prompts_with_hit / max(len(prompts), 1) * 100, 1),
        }
        state["status"] = "complete"
        state["current_provider"] = ""
        _model_test_state_set(run_id, state)
    except Exception as exc:
        logger.exception("model_test %s crashed", run_id)
        state["status"] = "failed"
        state["error"] = str(exc)[:500]
        _model_test_state_set(run_id, state)
