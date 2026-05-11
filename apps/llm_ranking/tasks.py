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
    from apps.llm_ranking.providers import (
        get_provider, get_provider_for_variant, parse_variant,
    )
    from apps.websites.models import Website

    import time as _time
    started_monotonic = _time.monotonic()

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

            state["prompt_rows"].append(row)
            _model_test_state_set(run_id, state)

        # Final summary
        results = state["prompt_rows"]
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

        # ── Post-processing: verbose synthesis + Gemini web grounding ──
        # Both steps are best-effort. A failure here is surfaced in the
        # state but does not mark the whole run as failed, since the raw
        # per-model responses are already valuable on their own.
        state["status"] = "analyzing"
        state["current_provider"] = ""
        state["analysis_status"] = "running"
        state["grounding_status"] = "running"
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


# ── Model Test post-processing helpers ─────────────────────────────

_SYNTHESIS_SYSTEM = (
    "You are a senior brand-visibility analyst. You read raw responses from "
    "multiple LLMs to brand-discovery prompts and produce a VERBOSE, "
    "decision-grade report for the marketing lead. You always cite specific "
    "prompts and exact phrases from the responses. You never invent data."
)


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
        f"Produce a verbose Markdown report with these sections, in order. "
        f"Do not skip sections. Be specific — quote exact phrases from the "
        f"raw data above and reference prompts by number.\n\n"
        f"## Headline finding\n"
        f"One sentence: did **{brand}** show up, where, and how strongly.\n\n"
        f"## Per-prompt breakdown\n"
        f"For each prompt (1..{prompt_count}), 2-4 sentences: what each "
        f"model said, who (if anyone) mentioned the brand, and what the "
        f"models suggested *instead* of the brand. Quote the exact "
        f"competitor names and product names that appeared.\n\n"
        f"## Per-model takeaway\n"
        f"One paragraph per model: how well it surfaced the brand, what "
        f"failure modes it showed (length, hallucination, refusal, generic "
        f"advice, etc), and how it compares to the other models.\n\n"
        f"## Themes the models discussed instead\n"
        f"A bulleted list of the dominant topics, competitors, and "
        f"categories that came up across responses — sorted by frequency. "
        f"Group by theme; cite the prompts where each appeared.\n\n"
        f"## What is missing from the prompts\n"
        f"Concrete suggestions for 3-5 ADDITIONAL prompts that, based on "
        f"how the models answered, are likely to surface the brand. "
        f"Explain each suggestion.\n\n"
        f"## Recommended next actions\n"
        f"A numbered list of 3-7 concrete content / SEO / brand-mention "
        f"interventions, ranked by likely impact. Each item names the "
        f"specific prompt that motivated it.\n"
    )

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


def _model_test_google_grounding(*, brand_terms, prompts, website) -> dict | None:
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

    # Citations are surfaced by the SDK as `grounding_metadata` on each
    # candidate. Shape varies; collect best-effort URLs without crashing
    # when the field is missing.
    citations: list[dict] = []
    try:
        cand = (getattr(response, "candidates", None) or [None])[0]
        gm = getattr(cand, "grounding_metadata", None) if cand else None
        chunks = getattr(gm, "grounding_chunks", None) if gm else None
        for ch in (chunks or []):
            web = getattr(ch, "web", None)
            if web is None:
                continue
            url = getattr(web, "uri", "") or ""
            title = getattr(web, "title", "") or url
            if url:
                citations.append({"url": url, "title": title})
    except Exception:
        citations = []

    return {
        "markdown": text,
        "citations": citations,
        "model": "gemini-1.5-pro",
        "grounded": used_grounding,
    }
