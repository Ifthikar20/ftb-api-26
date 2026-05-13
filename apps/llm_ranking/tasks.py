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

# Seconds to sleep BETWEEN each (prompt, model) cell. Small by design:
# just enough for the FE's 1.5s poll to catch the most recent result
# before the next call kicks off. The per-provider TokenBucket already
# enforces real rate limits — this pause is purely for UX pacing.
# Configurable via the MODEL_TEST_INTER_CALL_SLEEP_MS Django setting.
# 0 disables pacing entirely (back to flat-out fan-out).
MODEL_TEST_INTER_CALL_SLEEP_MS_DEFAULT = 250

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
    from apps.llm_ranking.providers import (
        get_provider, get_provider_for_variant, parse_variant,
    )
    from apps.websites.models import Website

    import time as _time
    started_monotonic = _time.monotonic()

    # Resolve pacing once per run so the worker doesn't import Django
    # settings 16+ times per audit.
    from django.conf import settings as _settings
    inter_call_ms = int(getattr(
        _settings, "MODEL_TEST_INTER_CALL_SLEEP_MS",
        MODEL_TEST_INTER_CALL_SLEEP_MS_DEFAULT,
    ))
    inter_call_sec = max(0.0, inter_call_ms / 1000.0)

    state = _model_test_state_get(run_id) or {}
    state.update({
        "status": "running",
        "website_id": str(website_id),
        "prompts": prompts,
        "providers": providers,
        "brand_terms": brand_terms,
        "total": len(prompts) * len(providers),
        "completed": 0,
        "current_prompt_index": 0,
        "current_provider": providers[0] if providers else "",
        "prompt_rows": [],
        "summary": None,
        "error": None,
        "user_id": user_id,
    })
    _model_test_state_set(run_id, state)

    try:
        website = Website.objects.filter(id=website_id).first()
        user = None
        if user_id is not None:
            user = get_user_model().objects.filter(id=user_id).first()

        brand_pat = _compile_brand_pattern(brand_terms)

        def _empty_metrics():
            return {
                "brand_mentioned": False,
                "mention_count": 0,
                "first_mention_pos": None,
                "prominence": 0.0,
                "list_rank": None,
                "list_size": None,
                "sentiment": None,
            }

        for p_idx, prompt_text in enumerate(prompts):
            row = {"prompt": prompt_text, "responses": []}
            state["current_prompt_index"] = p_idx
            for key in providers:
                state["current_provider"] = key
                _model_test_state_set(run_id, state)

                # `key` is a variant id ("<provider>:<model_id>") for new
                # clients, or a plain provider key for legacy callers.
                if parse_variant(key) is not None:
                    provider = get_provider_for_variant(key)
                else:
                    provider = get_provider(key)
                if provider is None or not provider.is_configured():
                    row["responses"].append({
                        "provider": key, "succeeded": False,
                        "error": "Provider not configured (missing API key).",
                        "response_text": "",
                        "duration_ms": 0,
                        **_empty_metrics(),
                    })
                else:
                    try:
                        pr = provider.query(
                            prompt_text, user=user, website=website,
                            audit_id="model_test", role="upstream",
                        )
                        text_out = getattr(pr, "text", "") or ""
                        metrics = _analyze_response(text_out, brand_pat)
                        row["responses"].append({
                            "provider": key,
                            "succeeded": bool(pr.succeeded),
                            "error": getattr(pr, "error", "") or "",
                            "response_text": text_out,
                            "response_chars": len(text_out),
                            "duration_ms": getattr(pr, "duration_ms", 0) or 0,
                            "input_tokens": int(getattr(pr, "input_tokens", 0) or 0),
                            "output_tokens": int(getattr(pr, "output_tokens", 0) or 0),
                            **metrics,
                        })
                    except Exception as exc:
                        logger.warning("model_test %s/%s failed: %s", run_id, key, exc)
                        row["responses"].append({
                            "provider": key, "succeeded": False,
                            "error": str(exc)[:300],
                            "response_text": "",
                            "duration_ms": 0,
                            **_empty_metrics(),
                        })

                state["completed"] = state.get("completed", 0) + 1
                _model_test_state_set(run_id, state)

                # Pace the next call so the UI catches up and we don't
                # burst the upstream. Skipped after the very last cell
                # since nothing follows.
                is_last_cell = (
                    p_idx == len(prompts) - 1
                    and key == providers[-1]
                )
                if inter_call_sec > 0 and not is_last_cell:
                    _time.sleep(inter_call_sec)

            state["prompt_rows"].append(row)
            _model_test_state_set(run_id, state)

        # Final summary
        results = state["prompt_rows"]
        prompts_with_hit = sum(
            1 for r in results if any(x["brand_mentioned"] for x in r["responses"])
        )
        hits = sum(1 for r in results for x in r["responses"] if x["brand_mentioned"])
        total_input_tokens = sum(
            int(x.get("input_tokens") or 0)
            for r in results for x in r["responses"]
        )
        total_output_tokens = sum(
            int(x.get("output_tokens") or 0)
            for r in results for x in r["responses"]
        )
        state["summary"] = {
            "prompts": len(prompts),
            "providers": providers,
            "total_runs": state["total"],
            "hits": hits,
            "prompts_with_hit": prompts_with_hit,
            "discovery_rate": round(prompts_with_hit / max(len(prompts), 1) * 100, 1),
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_tokens": total_input_tokens + total_output_tokens,
        }

        # ── Post-processing: sentiment + synthesis + Gemini grounding ──
        # All three steps are best-effort. A failure does not mark the
        # whole run as failed, since the raw per-model responses are
        # already valuable.
        state["status"] = "analyzing"
        state["current_provider"] = ""
        state["sentiment_status"] = "running"
        state["analysis_status"] = "running"
        state["grounding_status"] = "running"
        _model_test_state_set(run_id, state)

        # Sentiment classification (per hit response) + near-miss
        # detection (per non-hit response). Both run inside a single
        # batched LLM call via the synthesis provider — much cheaper
        # than two passes.
        try:
            classifications = _classify_responses(
                brand=brand_terms[0] if brand_terms else "",
                prompt_rows=results,
                website=website,
                user=user,
            )
            if classifications:
                for pi, row in enumerate(results):
                    for r in row.get("responses", []):
                        k = f"{pi}:{r.get('provider', '')}"
                        c = classifications.get(k)
                        if not c:
                            continue
                        if c.get("sentiment"):
                            r["sentiment"] = c["sentiment"]
                        if c.get("relevance"):
                            r["relevance"] = c["relevance"]
                        if c.get("evidence_phrase"):
                            r["evidence_phrase"] = c["evidence_phrase"]
                        if c.get("entities"):
                            r["entities"] = c["entities"]
                state["sentiment_status"] = "complete"
                state["prompt_rows"] = results
            else:
                state["sentiment_status"] = "skipped"
        except Exception as exc:
            logger.warning("model_test %s classification failed: %s", run_id, exc)
            state["sentiment_status"] = "failed"
            state["sentiment_error"] = str(exc)[:300]
        _model_test_state_set(run_id, state)

        # Skip synthesis when there's nothing useful to analyze. A run
        # where every cell failed produces only an error catalogue, not
        # a brand-visibility narrative — so we surface a one-line note
        # and move on rather than burning a synthesis token budget on
        # restating the failures.
        successful_calls = sum(
            1 for r in results for x in r.get("responses", []) if x.get("succeeded")
        )
        any_response_text = any(
            (x.get("response_text") or "").strip()
            for r in results for x in r.get("responses", [])
        )
        if successful_calls == 0 or not any_response_text:
            state["analysis"] = None
            state["analysis_status"] = "skipped"
            state["analysis_skip_reason"] = (
                "No model produced a response — nothing to analyze. "
                "Check provider API keys and SDK installation, then re-run."
            )
        else:
            try:
                state["analysis"] = _model_test_synthesize(
                    brand_terms=brand_terms,
                    prompts=prompts,
                    prompt_rows=results,
                    providers=providers,
                    user=user,
                    website=website,
                )
                state["analysis_status"] = "complete"
            except Exception as exc:
                logger.warning("model_test %s synthesis failed: %s", run_id, exc)
                state["analysis"] = None
                state["analysis_status"] = "failed"
                state["analysis_error"] = str(exc)[:300]
        _model_test_state_set(run_id, state)

        # Grounding is independent of model success — it researches the
        # brand on the open web — but it's wasteful to run on a clearly
        # broken environment. Skip when no model produced anything: the
        # user almost certainly has a config issue to fix first.
        if successful_calls == 0:
            state["google_grounding"] = None
            state["grounding_status"] = "skipped"
            state["grounding_skip_reason"] = (
                "Skipped because no model produced a response. "
                "Fix provider configuration and re-run to see web grounding."
            )
        else:
            try:
                state["google_grounding"] = _model_test_google_grounding(
                    brand_terms=brand_terms,
                    prompts=prompts,
                    website=website,
                    user_id=user_id,
                )
                state["grounding_status"] = "complete"
            except Exception as exc:
                logger.warning("model_test %s grounding failed: %s", run_id, exc)
                state["google_grounding"] = None
                state["grounding_status"] = "failed"
                state["grounding_error"] = str(exc)[:300]
        _model_test_state_set(run_id, state)

        state["status"] = "complete"
        _model_test_state_set(run_id, state)
    except Exception as exc:
        logger.exception("model_test %s crashed", run_id)
        state["status"] = "failed"
        state["error"] = str(exc)[:500]
        _model_test_state_set(run_id, state)
    finally:
        # Persist the final state to the database. This is what lets a
        # user reopen a run after the 1h Redis TTL has expired. Wrapped
        # in a broad try so a DB hiccup never tanks the in-memory state
        # the FE is still polling.
        try:
            _persist_model_test_run(
                run_id=run_id,
                website_id=website_id,
                user_id=user_id,
                state=state,
                duration_seconds=_time.monotonic() - started_monotonic,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("model_test %s persist failed: %s", run_id, exc)


def _persist_model_test_run(*, run_id, website_id, user_id, state, duration_seconds):
    """Write/update the durable ModelTestRun row mirroring `state`."""
    from django.utils import timezone
    from apps.llm_ranking.models import ModelTestRun

    defaults = dict(
        website_id=website_id,
        created_by_id=user_id,
        status=state.get("status") or "complete",
        prompts=state.get("prompts") or [],
        providers=state.get("providers") or [],
        brand_terms=state.get("brand_terms") or [],
        prompt_rows=state.get("prompt_rows") or [],
        summary=state.get("summary") or {},
        analysis=state.get("analysis"),
        analysis_status=state.get("analysis_status") or "",
        analysis_error=state.get("analysis_error") or "",
        google_grounding=state.get("google_grounding"),
        grounding_status=state.get("grounding_status") or "",
        grounding_error=state.get("grounding_error") or "",
        total_calls=int(state.get("total") or 0),
        completed_calls=int(state.get("completed") or 0),
        error_message=state.get("error") or "",
        completed_at=timezone.now(),
        duration_seconds=round(duration_seconds, 3),
    )
    ModelTestRun.objects.update_or_create(id=run_id, defaults=defaults)


# ── Model Test response analyzers ──────────────────────────────────

import re as _re

# Reasonably general list-item detector. Matches:
#   "1. ..."  "1) ..."  "1: ..."  "- ..."  "* ..."  "• ..."
# at the start of a (possibly indented) line, capturing the body.
_LIST_ITEM_RE = _re.compile(r"(?m)^[ \t]*(?:\d+[\.\)\:]|[-*•])[ \t]+(.+?)$")


def _compile_brand_pattern(terms):
    """Build a single case-insensitive regex with word boundaries.

    Sorting longest-first means "Acme Co" wins over "Acme" when both
    are aliases. Word boundaries (``\\b``) prevent "Apple" from matching
    "applesauce" or "Snapple", which was the biggest false-positive
    source under the old substring detector.
    """
    cleaned = sorted(
        [t.strip() for t in (terms or []) if t and t.strip()],
        key=len, reverse=True,
    )
    if not cleaned:
        return None
    escaped = [_re.escape(t) for t in cleaned]
    return _re.compile(r"\b(?:" + "|".join(escaped) + r")\b", _re.IGNORECASE)


def _detect_list_rank(text, pattern):
    """Find the brand's rank in a numbered/bulleted list, if any.

    Returns ``(rank, list_size)`` where rank is 1-indexed. Returns
    ``(None, list_size)`` when a list exists but the brand is in
    paragraph text instead of a list item. Returns ``(None, None)``
    when no list is detected at all.
    """
    if not text or pattern is None:
        return None, None
    items = _LIST_ITEM_RE.findall(text)
    if not items:
        return None, None
    for idx, body in enumerate(items, 1):
        if pattern.search(body):
            return idx, len(items)
    return None, len(items)


def _analyze_response(text, pattern):
    """Compute every per-response metric in one place.

    The returned dict is merged onto the response row. All FE metrics
    read these fields verbatim — there is no client-side recounting.
    """
    if not text or pattern is None:
        return {
            "brand_mentioned": False,
            "mention_count": 0,
            "first_mention_pos": None,
            "prominence": 0.0,
            "list_rank": None,
            "list_size": None,
            "sentiment": None,
        }
    matches = list(pattern.finditer(text))
    if not matches:
        rank, size = _detect_list_rank(text, pattern)  # surfaces list size
        return {
            "brand_mentioned": False,
            "mention_count": 0,
            "first_mention_pos": None,
            "prominence": 0.0,
            "list_rank": None,
            "list_size": size,
            "sentiment": None,
        }
    first_pos = matches[0].start()
    text_len = max(len(text), 1)
    # Prominence = how far from the start of the response the brand
    # first appeared, normalised by length. 1.0 = at the very start;
    # 0.0 = at the very end. This makes a mention at char 50 in a
    # 500-char reply rank above one at char 50 in a 5000-char reply.
    prominence = round(1.0 - (first_pos / text_len), 4)
    rank, size = _detect_list_rank(text, pattern)
    return {
        "brand_mentioned": True,
        "mention_count": len(matches),
        "first_mention_pos": first_pos,
        "prominence": prominence,
        "list_rank": rank,
        "list_size": size,
        "sentiment": None,  # filled later by _classify_response_sentiments
    }


# ── Model Test post-processing helpers ─────────────────────────────

_SYNTHESIS_SYSTEM = (
    "You are a senior brand-visibility analyst. You read raw responses from "
    "multiple LLMs to brand-discovery prompts and produce a VERBOSE, "
    "decision-grade report for the marketing lead. You always cite specific "
    "prompts and exact phrases from the responses. You never invent data."
)

_SENTIMENT_LABELS = {"positive", "neutral", "negative", "non_recommendation"}
_RELEVANCE_LABELS = {"direct", "near_miss", "category_match", "unrelated"}


def _classify_responses(*, brand, prompt_rows, user, website) -> dict:
    """Single batched LLM call that classifies every response.

    Returns ``{"<promptIdx>:<provider>": {sentiment, relevance, evidence_phrase}}``.

    - **sentiment** (only for direct hits): positive / neutral / negative /
      non_recommendation.
    - **relevance** (for every succeeded response): how close was the
      answer to actually surfacing the brand, even without naming it.
        - direct          — brand was literally named in the response.
        - near_miss       — a phrase describes the brand's exact product
                            or capability, but the brand name itself
                            is missing. Pure recoverable visibility win.
        - category_match  — the answer is about the brand's category /
                            problem space but doesn't describe the
                            brand's specific offering. Soft signal.
        - unrelated       — the response is off-topic entirely.
    - **evidence_phrase**: the exact ≤200-char quote that triggered the
      classification. Empty for ``direct`` (already in the text via
      highlighting) and ``unrelated`` (nothing useful to quote).

    Empty dict signals "skipped" to the caller.
    """
    from apps.llm_ranking.providers import get_synthesis_provider

    items = []
    for pi, row in enumerate(prompt_rows):
        prompt_text = row.get("prompt", "")
        for r in (row.get("responses") or []):
            if not r.get("succeeded"):
                continue
            text = (r.get("response_text") or "").strip()
            if not text:
                continue
            items.append({
                "pi": pi,
                "provider": r.get("provider", ""),
                "prompt": prompt_text,
                "text": text if len(text) <= 1800 else text[:1800] + " […]",
                "brand_mentioned": bool(r.get("brand_mentioned")),
            })
    if not items:
        return {}

    provider = get_synthesis_provider()
    if provider is None:
        return {}

    brand_label = (brand or "").strip() or "the brand"

    blocks = []
    for i, it in enumerate(items, 1):
        hint = "BRAND_LITERALLY_MENTIONED" if it["brand_mentioned"] else "BRAND_NOT_MENTIONED"
        blocks.append(
            f"### Response {i} [{hint}]\n"
            f"Question: {it['prompt']}\n"
            f"Answer: {it['text']}"
        )
    body = "\n\n".join(blocks)

    user_prompt = (
        f"Brand under test: **{brand_label}**\n\n"
        f"For each of the {len(items)} responses below, output ONE line "
        f"with FOUR fields separated by ` | `:\n\n"
        f"`Response <N>: <relevance> | <sentiment_or_none> | <evidence_phrase_or_none> | <entities_or_none>`\n\n"
        f"## relevance — pick exactly one:\n"
        f"- direct          — {brand_label} is literally named in the answer.\n"
        f"- near_miss       — the answer describes {brand_label}'s product, "
        f"capability, or value proposition in detail but never names the "
        f"brand.\n"
        f"- category_match  — the answer is in {brand_label}'s problem "
        f"space but doesn't describe what the brand specifically offers.\n"
        f"- unrelated       — the answer is about a different topic.\n\n"
        f"## sentiment — only when relevance == direct, else `none`:\n"
        f"- positive / neutral / negative / non_recommendation\n\n"
        f"## evidence_phrase — only when relevance is near_miss or "
        f"category_match, else `none`. A single direct quote from the "
        f"answer (≤200 chars, no ellipses, no paraphrasing).\n\n"
        f"## entities — comma-separated list of the most useful named "
        f"entities to highlight in the answer for an analyst (cap 12 "
        f"entries; each ≤80 chars). Prioritise in this order:\n"
        f"  1. Competitor / alternative business or product names\n"
        f"  2. Specific service offerings the answer recommends\n"
        f"  3. Place names (cities, neighbourhoods, addresses)\n"
        f"  4. Concrete product features or numeric specifications\n"
        f"Each entity must appear VERBATIM in the answer — no "
        f"paraphrasing or capitalisation changes. Skip the brand itself "
        f"({brand_label}) since it's already highlighted. Write `none` "
        f"if nothing useful to highlight.\n\n"
        f"=== RESPONSES ===\n{body}\n=== END ===\n\n"
        f"Output exactly {len(items)} lines in the format above. No "
        f"other text."
    )

    result = provider.query(
        user_prompt,
        system_prompt=(
            "You are a precise classification engine. Output only the "
            "requested labels and quotes, one line per response."
        ),
        user=user, website=website,
        audit_id="model_test_classify", role="synthesis",
    )
    if not result.succeeded:
        raise RuntimeError(result.error or "classifier failed")

    out: dict[str, dict] = {}
    # Tolerant parser. We expect 4 ` | `-separated fields. Older
    # tooling that only emits 3 still works via the fallback regex.
    line_re_4 = _re.compile(
        r"^\s*Response\s+(\d+)\s*:\s*([a-z_]+)\s*\|\s*([a-z_]+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*$",
        _re.IGNORECASE,
    )
    line_re_3 = _re.compile(
        r"^\s*Response\s+(\d+)\s*:\s*([a-z_]+)\s*\|\s*([a-z_]+)\s*\|\s*(.+?)\s*$",
        _re.IGNORECASE,
    )
    for line in (result.text or "").splitlines():
        m4 = line_re_4.match(line)
        m = m4 or line_re_3.match(line)
        if not m:
            continue
        idx = int(m.group(1)) - 1
        relevance = m.group(2).strip().lower()
        sentiment = m.group(3).strip().lower()
        phrase = m.group(4).strip()
        entities_raw = m.group(5).strip() if m4 else ""
        if not (0 <= idx < len(items)):
            continue
        if relevance not in _RELEVANCE_LABELS:
            continue
        entry: dict = {"relevance": relevance}
        if sentiment in _SENTIMENT_LABELS:
            entry["sentiment"] = sentiment
        if phrase and phrase.lower() != "none":
            cleaned = phrase.strip(' "\'`')
            if cleaned and len(cleaned) <= 240:
                entry["evidence_phrase"] = cleaned
        if entities_raw and entities_raw.lower() != "none":
            # Split on commas, strip surrounding quotes/spaces, cap
            # length and total count.
            parts = [p.strip(' "\'`') for p in entities_raw.split(",")]
            entities = [p for p in parts if p and len(p) <= 80][:12]
            if entities:
                entry["entities"] = entities
        it = items[idx]
        out[f"{it['pi']}:{it['provider']}"] = entry
    return out


def _model_test_synthesize(*, brand_terms, prompts, prompt_rows, providers,
                           user, website) -> dict | None:
    """
    Single LLM call that produces a verbose narrative analysis of the run.

    Pulls a configured synthesis provider (Deepseek → Claude → GPT-4
    fallback chain). Returns ``{ "markdown": "...", "provider": "..." }``
    or None when no tooling provider is configured.
    """
    from apps.llm_ranking.providers import get_synthesis_provider

    provider = get_synthesis_provider()
    if provider is None:
        return None

    brand = (brand_terms[0] if brand_terms else "the brand").strip() or "the brand"

    # Compact representation of every response so the synthesis LLM has
    # the full picture without us paying for 20k+ tokens of raw prose.
    blocks: list[str] = []
    for i, row in enumerate(prompt_rows, 1):
        blocks.append(f"### Prompt {i}: {row['prompt']}")
        for resp in row.get("responses", []):
            label = resp.get("provider", "?")
            hit = "BRAND_MENTIONED" if resp.get("brand_mentioned") else "no_mention"
            text = (resp.get("response_text") or "").strip()
            err = (resp.get("error") or "").strip()
            if text:
                snippet = text if len(text) <= 1200 else text[:1200] + " […]"
                blocks.append(f"- **{label}** [{hit}]\n{snippet}")
            elif err:
                blocks.append(f"- **{label}** [FAILED: {err}]")
    data = "\n\n".join(blocks)

    prompt_count = len(prompts)
    hit_count = sum(1 for r in prompt_rows if any(x.get("brand_mentioned") for x in r.get("responses", [])))

    user_prompt = (
        f"Brand under test: **{brand}**\n"
        f"Prompts tested: {prompt_count}\n"
        f"Prompts where at least one model mentioned the brand: {hit_count}\n"
        f"Models compared: {', '.join(providers)}\n\n"
        f"=== RAW RUN DATA ===\n{data}\n=== END RAW RUN DATA ===\n\n"
        f"Produce a SHORT, SCANNABLE Markdown report. Be terse. Prefer "
        f"bullets over paragraphs. Total output should fit in roughly "
        f"500 words. Cite specific competitors and quote short phrases "
        f"(<10 words) where useful. Skip any section that would have "
        f"no real signal.\n\n"
        f"## Bottom line\n"
        f"One sentence on whether **{brand}** surfaced and how strongly. "
        f"Then one sentence on the single biggest blocker.\n\n"
        f"## Prompts at a glance\n"
        f"Exactly one bullet per prompt (1..{prompt_count}). Format:\n"
        f"- **P#:** <verdict — mentioned / missed / failed> · <one-line "
        f"summary of what the models talked about instead, with a "
        f"competitor named if any>\n\n"
        f"## Models at a glance\n"
        f"One bullet per model. Format:\n"
        f"- **<model>:** <verdict — best / mid / missed / failed> · <one "
        f"specific behavioral note, e.g. \"named 3 competitors\", "
        f"\"returned generic framework\", \"401 auth error\">\n\n"
        f"## Top themes that surfaced instead of {brand}\n"
        f"3-5 bullets, sorted by frequency. Each bullet: theme name + "
        f"the prompts where it appeared, comma-separated as P1, P3.\n\n"
        f"## Three things to do next\n"
        f"Exactly 3 numbered actions, ranked by impact. Each ≤25 words.\n"
    )

    # The prompt above caps output at ~500 words (~750 tokens), which
    # fits inside every provider's default 1024-token reply budget.
    # Truncation issues we hit earlier were caused by the previous
    # "do not skip sections / be verbose" instruction blowing past
    # the cap, not by the cap itself.
    result = provider.query(
        user_prompt,
        system_prompt=_SYNTHESIS_SYSTEM,
        user=user, website=website,
        audit_id="model_test_synthesis", role="synthesis",
    )
    if not result.succeeded:
        raise RuntimeError(result.error or "synthesis call failed")
    return {
        "markdown": (result.text or "").strip(),
        "provider": getattr(provider, "name", ""),
        "model": getattr(provider, "model", ""),
        "duration_ms": getattr(result, "duration_ms", 0),
    }


# GEO ROI bucket per Aggarwal et al. 2024 "Generative Engine Optimization"
# (KDD '24), Table 2: relative visibility lift from GEO rewrites is
# strongly rank-dependent. Rank-1 sources usually lose, rank-4/5 gain
# the most. Anything below the top 5 we treat as "high" (already
# invisible — biggest upside).
def _geo_roi_bucket(rank):
    if rank is None:
        return "high"
    if rank <= 1:
        return "low"
    if rank <= 3:
        return "medium"
    return "high"


_GEO_ROI_ORDER = {"high": 0, "medium": 1, "low": 2}


def _model_test_google_grounding(*, brand_terms, prompts, website, user_id=None) -> dict | None:
    """
    One Gemini call with Google Search grounding to find live web context
    on the brand and (optionally) the topic of the prompts.

    Returns ``{ "markdown": "...", "citations": [...], "model": "..." }``
    or None when Gemini isn't configured. SDK quirks vary between
    versions; we try the modern path first and fall back to a no-tools
    call so we always return *something* useful when a key is present.
    """
    from django.conf import settings

    api_key = getattr(settings, "GEMINI_API_KEY", "")
    if not api_key:
        return None

    try:
        import google.generativeai as genai
    except ImportError:
        return None

    brand = (brand_terms[0] if brand_terms else "").strip() or "the brand"
    industry = ""
    if website is not None:
        industry = (getattr(website, "industry", "") or "").strip()
    topic_hint = f" in the {industry} space" if industry else ""

    grounding_prompt = (
        f"You are researching the live web presence of **{brand}**{topic_hint}.\n\n"
        f"Tasks (be verbose, cite sources):\n"
        f"1. Search the web for {brand}. Summarize the top 3-5 results "
        f"about the brand: what they say, who is publishing them, recency.\n"
        f"2. Search for competitors / alternatives in the same space. "
        f"List the 5 most-cited competitor names you find.\n"
        f"3. Search for the kinds of questions buyers are asking right "
        f"now in this space. Quote 3-5 example questions and what the "
        f"web answers with.\n"
        f"4. Based on all of the above, give a frank verdict: is {brand} "
        f"discoverable on the open web, and what's the single biggest "
        f"reason an LLM might not surface it when asked a buyer-style "
        f"question?\n\n"
        f"Use Markdown. Reference URLs you found in your search. Do not "
        f"answer from memory — base everything on fresh search results."
    )

    genai.configure(api_key=api_key)

    response = None
    used_grounding = False

    # Try modern grounding via `tools="google_search_retrieval"`.
    try:
        model = genai.GenerativeModel(
            "gemini-1.5-pro", tools="google_search_retrieval",
        )
        response = model.generate_content(grounding_prompt)
        used_grounding = True
    except Exception:
        # Older SDKs / unsupported regions: fall back to ungrounded
        # synthesis. Better than no answer at all.
        try:
            model = genai.GenerativeModel("gemini-1.5-pro")
            response = model.generate_content(grounding_prompt)
            used_grounding = False
        except Exception as exc:
            raise RuntimeError(f"Gemini grounding failed: {exc}")

    text = (getattr(response, "text", "") or "").strip()

    # Citations: query Google Programmable Search directly with the
    # user's prompts and the brand name. We used to surface Gemini's
    # `grounding_metadata.grounding_chunks` here, but those URIs are
    # opaque vertexaisearch.cloud.google.com redirects which made the
    # favicon/domain UI useless. Hitting CSE gives us the real
    # publisher URL up-front. Falls back to [] when the API isn't
    # configured — the markdown summary above is still useful on its
    # own, so we don't surface that as an error.
    from apps.llm_ranking.services.google_search import (
        is_configured as _cse_configured,
        search_many as _cse_search_many,
    )

    citations: list[dict] = []
    citations_source = "none"
    citations_stats: dict = {}
    if _cse_configured():
        cse_queries = [p for p in (prompts or []) if isinstance(p, str) and p.strip()]
        if brand and brand != "the brand":
            cse_queries = [brand] + cse_queries
        envelope = _cse_search_many(
            cse_queries,
            num_per_query=5,
            max_total=20,
            max_queries=15,
            user_id=user_id,
        )
        # Paper eq. 3: per-source Position-Adjusted Word Count over the
        # LLM response. Citations are keyed by their 1-indexed order in
        # the merged envelope, which is the same order the grounding
        # prompt was told to use ("[1]", "[2]", ...).
        from apps.llm_ranking.services import impression as _impression
        n_sources = len(envelope["citations"])
        imp_pwc = _impression.position_adjusted_word_counts(
            text or "",
            source_indices=range(1, n_sources + 1),
        )
        imp_wc = _impression.word_count_impression(
            text or "",
            source_indices=range(1, n_sources + 1),
        )
        citations = [
            {
                "url":      r["url"],
                "title":    r["title"],
                "snippet":  r.get("snippet", ""),
                "domain":   r.get("domain", ""),
                "queries":  r.get("queries", []),
                "serp_rank": r.get("best_serp_rank"),
                # GEO ROI bucket — Aggarwal et al. 2024 (KDD '24, Table 2)
                # show rank-1 sources LOSE visibility from GEO rewrites
                # (Cite Sources −30.3% at rank 1) while rank-5 sources GAIN
                # up to +115%. Low-rank-but-cited URLs are the place to spend
                # rewrite/optimization effort.
                "geo_roi":   _geo_roi_bucket(r.get("best_serp_rank")),
                # Paper eq. 3 / eq. 2 — both normalized to [0, 1].
                "impression_pwc": round(imp_pwc.get(idx, 0.0), 4),
                "impression_wc":  round(imp_wc.get(idx, 0.0), 4),
                # Paper Table 1 — average lift from the recommended
                # rewrite method, projected via eq. 4. ``None`` for
                # already-winning sources (low ROI bucket) since the
                # paper shows GEO rewrites can REGRESS rank-1 sources.
                "recommended_method": (
                    None
                    if _geo_roi_bucket(r.get("best_serp_rank")) == "low"
                    else _impression.best_method_for_domain(r.get("domain"))
                ),
                "projected_lift_pct": (
                    None
                    if _geo_roi_bucket(r.get("best_serp_rank")) == "low"
                    else _impression.projected_lift(
                        _impression.best_method_for_domain(r.get("domain"))
                    )
                ),
            }
            for idx, r in enumerate(envelope["citations"], start=1)
        ]
        # Surface the high-ROI count so the UI can frame the recommendation.
        citations = sorted(
            citations,
            key=lambda c: (_GEO_ROI_ORDER.get(c["geo_roi"], 99),
                           c["serp_rank"] if c["serp_rank"] is not None else 99),
        )
        citations_stats = {
            "queries_made":   envelope["queries_made"],
            "api_calls":      envelope["api_calls"],
            "cache_hits":     envelope["cache_hits"],
            "errors":         envelope["errors"],
            "quota_blocks":   envelope["quota_blocks"],
            "max_queries":    envelope["max_queries"],
            "max_total":      envelope["max_total"],
            "capped":         envelope["capped"],
            "quota_exceeded": envelope["quota_exceeded"],
            "daily_limit":    envelope["daily_limit"],
            "quota_remaining": envelope["quota_remaining"],
            "prompts_seen":   len(cse_queries),
        }
        if envelope["quota_exceeded"]:
            citations_source = "google_cse_quota"
        elif citations:
            citations_source = "google_cse"
        else:
            citations_source = "google_cse_empty"

    return {
        "markdown": text,
        "citations": citations,
        "citations_source": citations_source,
        "citations_stats": citations_stats,
        "model": "gemini-1.5-pro",
        "grounded": used_grounding,
    }
