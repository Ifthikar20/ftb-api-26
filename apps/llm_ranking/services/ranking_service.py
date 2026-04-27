"""
LLM Ranking Service — Generative Engine Optimization (GEO) audit.

Queries Claude, GPT-4, Gemini, and Perplexity with discovery prompts
and measures how prominently the business appears in AI-generated answers.
"""
import logging
import math
import re

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger("apps")


def wilson_ci(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Return (lower, upper) bounds of a Wilson score 95% CI for a proportion.

    Wilson is preferred over the normal approximation because it stays
    sensible when p is close to 0 or 1 and when n is small. Pure Python
    so we avoid pulling in scipy/statsmodels at call sites.
    """
    if n <= 0:
        return 0.0, 0.0
    p = successes / n
    denom = 1.0 + (z * z) / n
    centre = (p + (z * z) / (2.0 * n)) / denom
    half = (z / denom) * math.sqrt((p * (1.0 - p) / n) + (z * z) / (4.0 * n * n))
    return max(0.0, centre - half), min(1.0, centre + half)

# Providers and human labels
PROVIDERS = ["claude", "gpt4", "gemini", "perplexity"]

# Deterministic prompt templates live in apps.llm_ranking.services.prompt_library
# so callers can consume intent-tagged variants in the UI without duplicating
# the catalogue.

# System instruction to encourage numbered lists for accurate rank extraction
SYSTEM_INSTRUCTION = (
    "When listing tools, platforms, or products, please use a numbered list "
    "(1., 2., 3., etc.) and include a brief description for each. "
    "Be specific and mention actual product/company names."
)


def build_enriched_system_prompt(base_instruction: str, llm_context: str = "") -> str:
    """
    Build a system prompt that includes real business context.

    When the ContentEnricher has scanned the website, blogs, and Google,
    this injects all that data so the LLM responds with awareness of the
    actual business rather than relying only on its training data.
    """
    if not llm_context:
        return base_instruction

    return (
        f"{base_instruction}\n\n"
        f"IMPORTANT CONTEXT — The following is real, verified information about the "
        f"business being evaluated. Use this when ranking or mentioning the business:\n\n"
        f"{llm_context}"
    )


class LLMRankingService:

    # ── Prompt generation ──────────────────────────────────────────────────

    @staticmethod
    def generate_prompts(*, business_name: str, industry: str, description: str,
                         keywords: list, use_case: str = "",
                         location: str = "",
                         themes: list | None = None,
                         user=None, website=None) -> list[dict]:
        """
        Generate discovery prompts from business context.

        Returns a list of dicts: [{"text": str, "type": str}, ...]
        where type is the intent tag (recommendation, comparison, etc.).

        Uses the intent-balanced PromptLibrary for the deterministic base set,
        then asks Claude for additional natural-language variants to cover
        phrasings the library can't anticipate.
        """
        from apps.llm_ranking.services.prompt_library import (
            PromptLibrary, funnel_stage_for, rationale_for,
        )

        use_case = use_case or (keywords[0] if keywords else industry)

        # Library returns intent-tagged dicts including funnel_stage and a
        # short strategic rationale per prompt. Funnel stage drives the
        # default UI grouping; rationale renders as a sub-line beneath each
        # prompt so the user knows what the prompt actually tests.
        base_items = PromptLibrary.generate(
            industry=industry or "software",
            use_case=use_case,
            location=location,
            max_prompts=10,
            themes=themes,
            business_name=business_name,
        )
        # Normalise to {"text", "type", "funnel_stage", "rationale"}
        # ("type" is preserved for backwards compatibility with older clients)
        result_items = [
            {
                "text": p["text"],
                "type": p["intent"],
                "funnel_stage": p.get("funnel_stage", funnel_stage_for(p["intent"])),
                "rationale": p.get("rationale", rationale_for(
                    p["intent"], business_name=business_name, industry=industry,
                )),
            }
            for p in base_items
        ]

        # Use Claude to generate additional natural variants
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            loc_hint = f"\nLocation: {location}" if location else ""
            resp = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=512,
                messages=[{
                    "role": "user",
                    "content": (
                        f"Generate 4 short questions a buyer would ask an AI assistant "
                        f"when searching for a product like this:\n\n"
                        f"Business: {business_name}\n"
                        f"Industry: {industry}\n"
                        f"Description: {description}\n"
                        f"Keywords: {', '.join(keywords)}{loc_hint}\n\n"
                        "Return ONLY a JSON array of 4 question strings, no other text."
                    ),
                }],
            )
            import json
            import re as _re
            text = resp.content[0].text.strip()
            # Track token usage — tagged as prompt-generation so it's
            # distinguishable from upstream and extraction calls.
            try:
                from core.ai_tracking import record_usage
                record_usage(
                    module="llm_ranking", model_name="claude-sonnet-4-20250514",
                    input_tokens=resp.usage.input_tokens, output_tokens=resp.usage.output_tokens,
                    user=user, website=website,
                    metadata={"role": "prompt_generation"},
                )
            except Exception:
                pass
            match = _re.search(r"\[.*\]", text, _re.DOTALL)
            if match:
                ai_prompts = json.loads(match.group())
                for p in ai_prompts:
                    if isinstance(p, str):
                        result_items.append({
                            "text": p.strip(),
                            "type": "custom",
                            "funnel_stage": funnel_stage_for("custom"),
                            "rationale": rationale_for(
                                "custom", business_name=business_name,
                                industry=industry, use_case=use_case,
                            ),
                        })
        except Exception as e:
            logger.warning("Prompt generation via Claude failed: %s", e)

        # Deduplicate while preserving order
        seen = set()
        deduped = []
        for item in result_items:
            key = item["text"].strip().lower()
            if key not in seen:
                seen.add(key)
                deduped.append(item)
        return deduped[:10]  # cap at 10 prompts per audit

    # ── Per-provider query methods ─────────────────────────────────────────
    #
    # Provider integrations live in apps.llm_ranking.providers and share a
    # base class that records token usage centrally. The thin wrappers below
    # are kept so older callers / tests that import the static methods still
    # work, but new code should use providers.get_provider() directly.

    @staticmethod
    def _query_claude(prompt: str, system_prompt: str = "",
                      *, user=None, website=None, audit_id=None) -> tuple[bool, str, str]:
        from apps.llm_ranking.providers import ClaudeProvider
        result = ClaudeProvider().query(
            prompt, system_prompt, user=user, website=website, audit_id=audit_id,
        )
        return result.succeeded, result.text, result.error

    @staticmethod
    def _query_openai(prompt: str, system_prompt: str = "",
                      *, user=None, website=None, audit_id=None) -> tuple[bool, str, str]:
        from apps.llm_ranking.providers import OpenAIProvider
        result = OpenAIProvider().query(
            prompt, system_prompt, user=user, website=website, audit_id=audit_id,
        )
        return result.succeeded, result.text, result.error

    @staticmethod
    def _query_gemini(prompt: str, system_prompt: str = "",
                      *, user=None, website=None, audit_id=None) -> tuple[bool, str, str]:
        from apps.llm_ranking.providers import GeminiProvider
        result = GeminiProvider().query(
            prompt, system_prompt, user=user, website=website, audit_id=audit_id,
        )
        return result.succeeded, result.text, result.error

    @staticmethod
    def _query_perplexity(prompt: str, system_prompt: str = "",
                          *, user=None, website=None, audit_id=None) -> tuple[bool, str, str]:
        from apps.llm_ranking.providers import PerplexityProvider
        result = PerplexityProvider().query(
            prompt, system_prompt, user=user, website=website, audit_id=audit_id,
        )
        return result.succeeded, result.text, result.error

    # ── Response analysis ──────────────────────────────────────────────────

    @staticmethod
    def _analyze_mention(
        response_text: str,
        business_name: str,
        keywords: list,
    ) -> dict:
        """
        Detect if the business is mentioned, estimate its rank among listed items,
        and classify sentiment.

        IMPORTANT: Keywords are used for DETECTION only (is the business somewhere
        in the response?). For RANK extraction, only the business name is used
        to avoid false positives (e.g. keyword "analytics" matching "Google Analytics").

        Returns a dict with:
          is_mentioned, mention_rank, sentiment, confidence_score, mention_context
        """
        text_lower = response_text.lower()
        name_lower = business_name.lower().strip()

        # Build TWO sets of search terms:
        # 1. name_terms: name + name words only (precise — for rank extraction)
        # 2. all_terms: name_terms + keywords (broad — for is_mentioned detection)
        name_terms = []
        if name_lower:
            name_terms.append(name_lower)
            for word in name_lower.split():
                if len(word) > 3 and word not in name_terms:
                    name_terms.append(word)

        all_terms = list(name_terms)
        for k in keywords:
            k_lower = k.lower().strip()
            if k_lower and len(k_lower) > 3 and k_lower not in all_terms:
                all_terms.append(k_lower)

        # Detection: use ALL terms (name + keywords)
        is_mentioned = any(term in text_lower for term in all_terms if term)

        if not is_mentioned:
            return {
                "is_mentioned": False,
                "mention_rank": None,
                "sentiment": "not_mentioned",
                "confidence_score": 95.0,
                "mention_context": "",
            }

        # ── Rank extraction (use ONLY name_terms, not keywords) ──
        lines = response_text.split("\n")
        rank = None
        context = ""
        item_index = 0

        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue

            is_list_item = False

            if re.match(r"^(\d+)[\.\)\:\s]+\s*", line_stripped):
                is_list_item = True
            elif re.match(r"^#{1,4}\s+(\d+[\.\)]\s+)?", line_stripped):
                is_list_item = True
            elif re.match(r"^[-*•]\s+", line_stripped):
                is_list_item = True
            elif re.match(r"^\*\*[^*]+\*\*", line_stripped):
                is_list_item = True

            if is_list_item:
                item_index += 1
                line_lower = line_stripped.lower()
                if any(term in line_lower for term in name_terms if term):
                    rank = item_index
                    context = line_stripped[:300]
                    break
            else:
                line_lower = line_stripped.lower()
                if any(term in line_lower for term in name_terms if term) and not context:
                    context = line_stripped[:300]

        # If detected via keywords but name not found anywhere, lower confidence
        keyword_only = not any(term in text_lower for term in name_terms if term)

        sentiment = LLMRankingService._classify_sentiment(
            context=context or response_text[:500],
            business_name=business_name,
        )

        if keyword_only:
            confidence = 40.0
        elif rank is not None:
            confidence = 90.0
        else:
            confidence = 70.0

        return {
            "is_mentioned": True,
            "mention_rank": rank,
            "sentiment": sentiment,
            "confidence_score": confidence,
            "mention_context": context,
        }


    @staticmethod
    def _classify_sentiment(*, context: str, business_name: str) -> str:
        """Quick heuristic sentiment classification."""
        context_lower = context.lower()
        positive_signals = [
            "recommend", "best", "top", "leading", "excellent", "great", "popular",
            "trusted", "powerful", "easy", "effective", "reliable", "industry-leading",
            "innovative", "standout", "favorite", "preferred", "robust", "comprehensive",
        ]
        negative_signals = [
            "avoid", "poor", "bad", "expensive", "difficult", "limited",
            "unreliable", "not recommended", "worse", "lacking", "outdated",
            "steep learning curve", "overpriced", "clunky",
        ]
        pos = sum(1 for s in positive_signals if s in context_lower)
        neg = sum(1 for s in negative_signals if s in context_lower)
        if pos > neg:
            return "positive"
        if neg > pos:
            return "negative"
        return "neutral"

    # ── Scoring ────────────────────────────────────────────────────────────

    @staticmethod
    def compute_overall_score(results: list) -> dict:
        """
        Compute aggregate metrics from a list of LLMRankingResult objects.

        Returns dict with overall_score, mention_rate, avg_mention_rank,
        and 95% Wilson CI bounds on the mention rate (percent units).
        """
        total = len(results)
        if not total:
            return {
                "overall_score": 0,
                "mention_rate": 0.0,
                "avg_mention_rank": 0.0,
                "mention_rate_ci_lower": 0.0,
                "mention_rate_ci_upper": 0.0,
            }

        succeeded = [r for r in results if r.query_succeeded]
        mentioned = [r for r in succeeded if r.is_mentioned]
        mention_rate = len(mentioned) / len(succeeded) * 100 if succeeded else 0.0

        ci_low, ci_high = wilson_ci(len(mentioned), len(succeeded))

        ranks = [r.mention_rank for r in mentioned if r.mention_rank is not None]
        avg_rank = sum(ranks) / len(ranks) if ranks else 0.0

        # Score formula:
        #   40% mention rate (0-40 pts)
        #   30% rank bonus: top-3 mentions add more (0-30 pts)
        #   20% sentiment (positive=20, neutral=10, negative=0)
        #   10% provider coverage bonus (queried ≥3 providers)
        mention_score = mention_rate * 0.40

        rank_score = 0.0
        if ranks:
            # avg rank 1 = 30pts, avg rank 5 = 10pts, avg rank >10 = 5pts
            if avg_rank <= 1:
                rank_score = 30.0
            elif avg_rank <= 3:
                rank_score = 20.0
            elif avg_rank <= 5:
                rank_score = 15.0
            elif avg_rank <= 10:
                rank_score = 10.0
            else:
                rank_score = 5.0

        positive = sum(1 for r in mentioned if r.sentiment == "positive")
        neutral = sum(1 for r in mentioned if r.sentiment == "neutral")
        if mentioned:
            sentiment_score = ((positive * 20) + (neutral * 10)) / len(mentioned)
        else:
            sentiment_score = 0.0

        provider_count = len({r.provider for r in succeeded})
        coverage_bonus = 10.0 if provider_count >= 3 else (provider_count / 3 * 10)

        overall = int(min(100, mention_score + rank_score + sentiment_score + coverage_bonus))
        return {
            "overall_score": overall,
            "mention_rate": round(mention_rate, 1),
            "avg_mention_rank": round(avg_rank, 1),
            "mention_rate_ci_lower": round(ci_low * 100, 1),
            "mention_rate_ci_upper": round(ci_high * 100, 1),
        }

    # ── Chord-style audit runner (preferred at scale) ──────────────────────
    #
    # The audit pipeline is split into three pieces so it can fan out across
    # Celery workers:
    #   prepare_audit   — synchronous prep (enrichment, status flip)
    #   run_audit_cell  — one (prompt, provider) cell, idempotent
    #   finalise_audit  — chord callback, computes aggregate score + cost
    #
    # The legacy run_audit() below remains for tests that run the whole
    # pipeline in-process (CELERY_TASK_ALWAYS_EAGER=True).

    @staticmethod
    def prepare_audit(*, audit_id: str) -> dict | None:
        """
        Run enrichment + flip the audit to RUNNING. Returns the plan dict the
        Celery task uses to fan out cells, or None if the audit isn't runnable.
        """
        from apps.llm_ranking.models import LLMRankingAudit, LLMRankingResult

        try:
            audit = LLMRankingAudit.objects.select_related("website").get(id=audit_id)
        except LLMRankingAudit.DoesNotExist:
            logger.error("LLMRankingAudit %s not found", audit_id)
            return None

        # Filter requested providers down to those that are implemented.
        from apps.llm_ranking.providers import PROVIDERS
        provider_keys = [p for p in (audit.providers_queried or []) if p in PROVIDERS]
        if not provider_keys:
            audit.status = LLMRankingAudit.STATUS_FAILED
            audit.error_message = "No implemented providers selected for this audit."
            audit.save(update_fields=["status", "error_message", "updated_at"])
            return None

        # Normalise prompt list to {"text", "type"}.
        prompt_items = []
        for p in (audit.prompts or []):
            if isinstance(p, dict):
                prompt_items.append({"text": p.get("text", ""), "type": p.get("type", "custom")})
            else:
                prompt_items.append({"text": str(p), "type": "custom"})
        prompt_items = [p for p in prompt_items if p["text"].strip()]
        if not prompt_items:
            audit.status = LLMRankingAudit.STATUS_FAILED
            audit.error_message = "Audit has no prompts."
            audit.save(update_fields=["status", "error_message", "updated_at"])
            return None

        def _audit_log(msg, level="info"):
            entry = {"ts": timezone.now().isoformat(), "level": level, "msg": msg}
            logs = list(audit.audit_logs or [])
            logs.append(entry)
            audit.audit_logs = logs

        _audit_log(f"Starting audit for {audit.business_name} ({audit.industry})")
        _audit_log(f"Selected LLM providers: {', '.join(provider_keys)}")

        # Enrichment — same as the legacy path.
        enriched_context = ""
        try:
            from apps.llm_ranking.services.content_enricher import ContentEnricher

            extra_urls = []
            for entry in (getattr(audit, "context_urls", None) or []):
                if isinstance(entry, dict):
                    extra_urls.append(entry.get("url", ""))
                elif isinstance(entry, str):
                    extra_urls.append(entry)
            extra_urls = [u for u in extra_urls if u]

            _audit_log(f"🔍 Scanning main website: {audit.website.url}")
            enrichment = ContentEnricher.enrich(
                main_url=audit.website.url,
                extra_urls=extra_urls,
                business_name=audit.business_name,
                industry=audit.industry,
                include_google=True,
            )
            enriched_context = enrichment.get("llm_context", "")
            if enriched_context:
                _audit_log(
                    f"📦 Context assembled — {len(enriched_context):,} chars of business intelligence",
                    "success",
                )
        except Exception as exc:
            logger.warning("Content enrichment failed for audit %s: %s", audit_id, exc)
            _audit_log(f"⚠️ Content enrichment failed: {str(exc)[:100]}", "warn")

        total = len(prompt_items) * len(provider_keys)
        _audit_log(
            f"🚀 Running {total} queries ({len(prompt_items)} prompts × {len(provider_keys)} providers)"
        )

        audit.status = LLMRankingAudit.STATUS_RUNNING
        audit.total_queries = total
        audit.queries_completed = 0
        audit.started_at = timezone.now()
        audit.providers_queried = provider_keys
        # Snapshot the enriched context onto the audit so cells don't have to
        # rescrape. Stored as a single string field via JSON to keep the schema
        # change minimal — context_urls already accepts arbitrary structure.
        existing_ctx = list(audit.context_urls or [])
        existing_ctx_strings = [c for c in existing_ctx if isinstance(c, dict) and c.get("kind") == "_enriched"]
        if existing_ctx_strings:
            for c in existing_ctx_strings:
                c["text"] = enriched_context
        else:
            existing_ctx.append({"kind": "_enriched", "text": enriched_context})
        audit.context_urls = existing_ctx

        audit.save(update_fields=[
            "status", "total_queries", "queries_completed", "started_at",
            "providers_queried", "audit_logs", "context_urls", "updated_at",
        ])
        return {"prompts": prompt_items, "providers": provider_keys}

    @staticmethod
    def run_audit_cell(*, audit_id: str, prompt_index: int, provider: str) -> dict:
        """
        Execute a single (prompt, provider) cell. Idempotent: uses
        update_or_create on (audit, prompt_index, provider, run_id=0) so a
        retried task can never produce a second row for the same cell.
        """
        from apps.llm_ranking.models import LLMRankingAudit, LLMRankingResult
        from apps.llm_ranking.providers import get_provider
        from apps.llm_ranking.services.extraction_service import HaikuExtractionService

        audit = LLMRankingAudit.objects.select_related("website").get(id=audit_id)
        prompts = audit.prompts or []
        if prompt_index >= len(prompts):
            return {"skipped": True, "reason": "prompt_index out of range"}

        prompt_entry = prompts[prompt_index]
        prompt_text = prompt_entry.get("text") if isinstance(prompt_entry, dict) else str(prompt_entry)
        prompt_text = (prompt_text or "").strip()
        if not prompt_text:
            return {"skipped": True, "reason": "empty prompt"}

        # Restore enriched context snapshot.
        enriched_context = ""
        for c in (audit.context_urls or []):
            if isinstance(c, dict) and c.get("kind") == "_enriched":
                enriched_context = c.get("text", "")
                break
        sys_prompt = (
            build_enriched_system_prompt(SYSTEM_INSTRUCTION, enriched_context)
            if enriched_context else ""
        )

        provider_inst = get_provider(provider)
        if provider_inst is None:
            # Provider not configured — record a failure row so aggregation
            # sees the cell as terminal.
            LLMRankingService._upsert_failed_cell(
                audit=audit, prompt_index=prompt_index, provider=provider,
                prompt_text=prompt_text,
                error=f"{provider} not configured or implemented",
            )
            LLMRankingService._bump_progress(audit_id)
            return {"audit_id": audit_id, "prompt_index": prompt_index,
                    "provider": provider, "succeeded": False}

        result = provider_inst.query(
            prompt_text, sys_prompt,
            user=audit.created_by, website=audit.website,
            audit_id=str(audit.id),
        )

        analysis = LLMRankingService._empty_analysis()
        if result.succeeded:
            try:
                analysis = HaikuExtractionService.extract(
                    response_text=result.text,
                    brand_name=audit.business_name,
                    keywords=audit.keywords,
                    user=audit.created_by,
                    website=audit.website,
                    audit_id=str(audit.id),
                )
            except Exception as exc:
                logger.warning(
                    "Extraction failed for audit %s cell (%d/%s): %s",
                    audit_id, prompt_index, provider, exc,
                )

        LLMRankingResult.objects.update_or_create(
            audit=audit, prompt_index=prompt_index, provider=provider, run_id=0,
            defaults={
                "prompt": prompt_text,
                "response_text": result.text or "",
                "is_mentioned": analysis["is_mentioned"],
                "mention_rank": analysis["mention_rank"],
                "sentiment": analysis["sentiment"],
                "confidence_score": analysis["confidence_score"],
                "mention_context": analysis["mention_context"],
                "query_succeeded": result.succeeded,
                "error_message": (result.error or "")[:500],
                "is_linked": analysis.get("is_linked", False),
                "competitors_mentioned": analysis.get("competitors_mentioned", []),
                "primary_recommendation": analysis.get("primary_recommendation", ""),
                "citations": analysis.get("citations", []),
                "extraction_model": analysis.get("extraction_model", ""),
                "extraction_version": analysis.get("extraction_version", ""),
            },
        )
        LLMRankingService._bump_progress(audit_id)
        return {
            "audit_id": audit_id, "prompt_index": prompt_index,
            "provider": provider, "succeeded": result.succeeded,
        }

    @staticmethod
    def _empty_analysis() -> dict:
        from apps.llm_ranking.models import LLMRankingResult
        return {
            "is_mentioned": False,
            "mention_rank": None,
            "sentiment": LLMRankingResult.SENTIMENT_NOT_MENTIONED,
            "confidence_score": 0.0,
            "mention_context": "",
            "is_linked": False,
            "competitors_mentioned": [],
            "primary_recommendation": "",
            "citations": [],
            "extraction_model": "",
            "extraction_version": "",
        }

    @staticmethod
    def _upsert_failed_cell(*, audit, prompt_index, provider, prompt_text, error):
        from apps.llm_ranking.models import LLMRankingResult
        analysis = LLMRankingService._empty_analysis()
        LLMRankingResult.objects.update_or_create(
            audit=audit, prompt_index=prompt_index, provider=provider, run_id=0,
            defaults={
                "prompt": prompt_text,
                "response_text": "",
                "is_mentioned": False,
                "mention_rank": None,
                "sentiment": analysis["sentiment"],
                "confidence_score": 0.0,
                "mention_context": "",
                "query_succeeded": False,
                "error_message": (error or "")[:500],
                "competitors_mentioned": [],
                "citations": [],
                "extraction_model": "",
                "extraction_version": "",
            },
        )

    @staticmethod
    def _bump_progress(audit_id: str) -> None:
        """Atomically increment queries_completed so the live UI ETAs work."""
        from django.db.models import F
        from apps.llm_ranking.models import LLMRankingAudit
        LLMRankingAudit.objects.filter(id=audit_id).update(
            queries_completed=F("queries_completed") + 1,
        )

    @staticmethod
    def finalise_audit(*, audit_id: str) -> None:
        """Chord callback — compute aggregates, roll up cost, mark completed."""
        from apps.llm_ranking.models import LLMRankingAudit, LLMRankingResult

        try:
            audit = LLMRankingAudit.objects.get(id=audit_id)
        except LLMRankingAudit.DoesNotExist:
            return

        all_results = list(audit.results.all())
        scores = LLMRankingService.compute_overall_score(all_results)

        # Cost roll-up — only rows tagged with this audit's id.
        try:
            from django.db.models import Sum
            from apps.accounts.models import AITokenUsage
            spend = (
                AITokenUsage.objects
                .filter(metadata__audit_id=str(audit.id))
                .aggregate(tokens=Sum("total_tokens"), cost=Sum("estimated_cost_usd"))
            )
            audit.total_tokens = int(spend["tokens"] or 0)
            audit.total_cost_usd = spend["cost"] or 0
        except Exception as exc:
            logger.warning("Cost roll-up failed for audit %s: %s", audit_id, exc)

        providers_with_any_success = sorted({
            r.provider for r in all_results if r.query_succeeded
        })

        audit.status = LLMRankingAudit.STATUS_COMPLETED
        audit.overall_score = scores["overall_score"]
        audit.mention_rate = scores["mention_rate"]
        audit.avg_mention_rank = scores["avg_mention_rank"]
        audit.mention_rate_ci_lower = scores["mention_rate_ci_lower"]
        audit.mention_rate_ci_upper = scores["mention_rate_ci_upper"]
        audit.providers_queried = providers_with_any_success or audit.providers_queried
        audit.extraction_method = LLMRankingAudit.EXTRACTION_LLM
        audit.completed_at = timezone.now()
        if audit.started_at:
            audit.duration_seconds = (audit.completed_at - audit.started_at).total_seconds()

        logs = list(audit.audit_logs or [])
        logs.append({
            "ts": timezone.now().isoformat(), "level": "success",
            "msg": (
                f"🏁 AUDIT COMPLETE — Score {scores['overall_score']}/100, "
                f"mention rate {scores['mention_rate']:.1f}%, "
                f"cost ${float(audit.total_cost_usd):.4f}"
            ),
        })
        audit.audit_logs = logs

        audit.save(update_fields=[
            "status", "overall_score", "mention_rate", "avg_mention_rank",
            "mention_rate_ci_lower", "mention_rate_ci_upper",
            "providers_queried", "extraction_method", "completed_at",
            "duration_seconds", "total_tokens", "total_cost_usd",
            "audit_logs", "updated_at",
        ])

    # ── Legacy single-task runner (eager mode + tests) ─────────────────────

    @staticmethod
    def run_audit(*, audit_id: str) -> None:
        """
        Execute a full LLM ranking audit. Called as a Celery task.
        Updates the audit record with results and computed scores.
        Saves progress after each query so the frontend can show ETA.
        """
        from apps.llm_ranking.models import LLMRankingAudit, LLMRankingResult

        def _audit_log(audit_obj, msg, level="info"):
            """Append a timestamped log entry and persist immediately."""
            entry = {
                "ts": timezone.now().isoformat(),
                "level": level,
                "msg": msg,
            }
            logs = list(audit_obj.audit_logs or [])
            logs.append(entry)
            audit_obj.audit_logs = logs
            try:
                audit_obj.save(update_fields=["audit_logs", "updated_at"])
            except Exception:
                pass  # non-critical

        try:
            audit = LLMRankingAudit.objects.select_related("website").get(id=audit_id)
        except LLMRankingAudit.DoesNotExist:
            logger.error("LLMRankingAudit %s not found", audit_id)
            return

        provider_map = {
            LLMRankingResult.PROVIDER_CLAUDE: LLMRankingService._query_claude,
            LLMRankingResult.PROVIDER_GPT4: LLMRankingService._query_openai,
            LLMRankingResult.PROVIDER_GEMINI: LLMRankingService._query_gemini,
            LLMRankingResult.PROVIDER_PERPLEXITY: LLMRankingService._query_perplexity,
        }

        # Only query user-selected providers (stored at audit creation)
        selected_providers = audit.providers_queried or list(provider_map.keys())
        # Filter to only providers that have a query function
        selected_providers = [p for p in selected_providers if p in provider_map]

        _audit_log(audit, f"Starting audit for {audit.business_name} ({audit.industry})")
        _audit_log(audit, f"Selected LLM providers: {', '.join(selected_providers)}")

        # ── Content enrichment: scan URLs + Google ────────────────────────
        # Build rich context from the website, user-provided URLs, and Google
        enriched_context = ""
        try:
            from apps.llm_ranking.services.content_enricher import ContentEnricher

            # Get extra URLs from the audit (stored at creation time)
            extra_urls = []
            context_urls_raw = getattr(audit, 'context_urls', None) or []
            for entry in context_urls_raw:
                if isinstance(entry, dict):
                    extra_urls.append(entry.get("url", ""))
                elif isinstance(entry, str):
                    extra_urls.append(entry)
            extra_urls = [u for u in extra_urls if u]

            _audit_log(audit, f"🔍 Scanning main website: {audit.website.url}")
            if extra_urls:
                _audit_log(audit, f"🔍 Scanning {len(extra_urls)} extra URL(s): {', '.join(u[:50] for u in extra_urls)}")

            enrichment = ContentEnricher.enrich(
                main_url=audit.website.url,
                extra_urls=extra_urls,
                business_name=audit.business_name,
                industry=audit.industry,
                include_google=True,
            )
            enriched_context = enrichment.get("llm_context", "")

            # Log what was found
            main_scan = enrichment.get("main_scan", {})
            if main_scan.get("success"):
                products = main_scan.get("products", [])
                _audit_log(audit, f"✅ Website scanned — found {len(products)} product(s)/service(s)", "success")
            else:
                _audit_log(audit, f"⚠️ Website scan returned no data", "warn")

            extra_scans = enrichment.get("extra_scans", [])
            for scan in extra_scans:
                url_short = scan.get("url", "")[:60]
                if scan.get("success"):
                    _audit_log(audit, f"✅ Scanned: {url_short}", "success")
                else:
                    _audit_log(audit, f"⚠️ Failed to scan: {url_short}", "warn")

            google_snippets = enrichment.get("google_snippets", [])
            if google_snippets:
                _audit_log(audit, f"🌐 Google Search: found {len(google_snippets)} competitive snippet(s)", "success")

            _audit_log(audit, f"📦 Context assembled — {len(enriched_context):,} chars of business intelligence")

            logger.info(
                "Content enrichment complete for audit %s — %d extra URLs, context length: %d",
                audit_id, len(extra_urls), len(enriched_context),
            )
        except Exception as exc:
            logger.warning("Content enrichment failed for audit %s: %s", audit_id, exc)
            _audit_log(audit, f"⚠️ Content enrichment failed: {str(exc)[:100]}", "warn")
            # Non-fatal — audit continues with basic prompts

        # Build the enriched system prompt for Claude
        enriched_system = build_enriched_system_prompt(SYSTEM_INSTRUCTION, enriched_context)
        if enriched_context:
            _audit_log(audit, "🧠 Enriched system prompt ready — Claude will see full business context")

        # Calculate total queries and set progress tracking
        # Prompts may be structured [{"text": ..., "type": ...}] or flat ["..."]
        prompt_items = []
        for p in audit.prompts:
            if isinstance(p, dict):
                prompt_items.append({"text": p.get("text", ""), "type": p.get("type", "custom")})
            else:
                prompt_items.append({"text": str(p), "type": "custom"})

        total = len(selected_providers) * len(prompt_items)
        _audit_log(audit, f"🚀 Running {total} queries ({len(prompt_items)} prompts × {len(selected_providers)} providers)")
        audit.status = LLMRankingAudit.STATUS_RUNNING
        audit.total_queries = total
        audit.queries_completed = 0
        audit.started_at = timezone.now()
        audit.save(update_fields=[
            "status", "total_queries", "queries_completed", "started_at", "updated_at",
        ])

        all_results = []
        providers_succeeded = []
        completed = 0

        PROVIDER_LABELS = {
            'claude': 'Claude', 'gpt4': 'GPT-4', 'gemini': 'Gemini',
            'perplexity': 'Perplexity', 'meta_llama': 'Meta Llama',
            'mistral': 'Mistral', 'cohere': 'Cohere', 'deepseek': 'DeepSeek',
            'grok': 'Grok', 'amazon_nova': 'Amazon Nova',
        }

        for provider in selected_providers:
            query_fn = provider_map.get(provider)
            if not query_fn:
                continue

            plabel = PROVIDER_LABELS.get(provider, provider)
            _audit_log(audit, f"━━━ Querying {plabel} ━━━")

            for prompt_item in prompt_items:
                prompt_text = prompt_item["text"]
                prompt_short = prompt_text[:80] + ('...' if len(prompt_text) > 80 else '')
                _audit_log(audit, f"📤 → {plabel}: \"{prompt_short}\"")

                try:
                    # All providers get the enriched context when available.
                    # user/website/audit_id are passed through so each call's
                    # token usage is attributed to the right user in Settings.
                    sys_prompt = enriched_system if enriched_context else ""
                    succeeded, response_text, error = query_fn(
                        prompt_text, sys_prompt,
                        user=audit.created_by, website=audit.website,
                        audit_id=str(audit.id),
                    )
                except Exception as exc:
                    succeeded, response_text, error = False, "", str(exc)
                    logger.warning("Provider %s threw for audit %s: %s", provider, audit_id, exc)
                    _audit_log(audit, f"❌ {plabel} error: {str(exc)[:80]}", "error")

                if succeeded:
                    resp_len = len(response_text)
                    _audit_log(audit, f"📥 ← {plabel} responded ({resp_len:,} chars) — extracting mentions...", "success")
                    from apps.llm_ranking.services.extraction_service import (
                        HaikuExtractionService,
                    )
                    analysis = HaikuExtractionService.extract(
                        response_text=response_text,
                        brand_name=audit.business_name,
                        keywords=audit.keywords,
                        user=audit.created_by,
                        website=audit.website,
                        audit_id=str(audit.id),
                    )
                    # Log extraction result
                    if analysis["is_mentioned"]:
                        rank = analysis.get("mention_rank") or "?"
                        sentiment = analysis.get("sentiment", "neutral")
                        _audit_log(audit, f"🏆 {audit.business_name} mentioned at rank #{rank} — sentiment: {sentiment}", "success")
                    else:
                        _audit_log(audit, f"👻 {audit.business_name} NOT mentioned in response", "warn")
                    competitors = analysis.get("competitors_mentioned", [])
                    if competitors:
                        _audit_log(audit, f"   ↳ Competitors found: {', '.join(competitors[:5])}")
                else:
                    _audit_log(audit, f"❌ {plabel} query failed: {error[:80]}", "error")
                    analysis = {
                        "is_mentioned": False,
                        "mention_rank": None,
                        "sentiment": LLMRankingResult.SENTIMENT_NOT_MENTIONED,
                        "confidence_score": 0.0,
                        "mention_context": "",
                        "is_linked": False,
                        "competitors_mentioned": [],
                        "primary_recommendation": "",
                        "citations": [],
                        "extraction_model": "",
                        "extraction_version": "",
                    }

                result = LLMRankingResult.objects.create(
                    audit=audit,
                    provider=provider,
                    prompt=prompt_text,

                    response_text=response_text,
                    is_mentioned=analysis["is_mentioned"],
                    mention_rank=analysis["mention_rank"],
                    sentiment=analysis["sentiment"],
                    confidence_score=analysis["confidence_score"],
                    mention_context=analysis["mention_context"],
                    query_succeeded=succeeded,
                    error_message=error,
                    is_linked=analysis.get("is_linked", False),
                    competitors_mentioned=analysis.get("competitors_mentioned", []),
                    primary_recommendation=analysis.get("primary_recommendation", ""),
                    citations=analysis.get("citations", []),
                    extraction_model=analysis.get("extraction_model", ""),
                    extraction_version=analysis.get("extraction_version", ""),
                )
                all_results.append(result)

                # Update progress after each query
                completed += 1
                audit.queries_completed = completed
                audit.save(update_fields=["queries_completed", "updated_at"])

            provider_results = [r for r in all_results if r.provider == provider]
            prov_mentioned = sum(1 for r in provider_results if r.is_mentioned)
            if any(r.provider == provider and r.query_succeeded for r in all_results):
                providers_succeeded.append(provider)
            _audit_log(audit, f"✅ {plabel} done — mentioned in {prov_mentioned}/{len(provider_results)} responses", "success")

        # Compute aggregate scores
        _audit_log(audit, "📊 Computing aggregate scores...")
        scores = LLMRankingService.compute_overall_score(all_results)

        # Roll up token + cost spend for this audit. We tagged every record
        # with metadata.audit_id, so we can sum exactly the rows this run
        # produced (upstream + extraction + any prompt-generation).
        try:
            from django.db.models import Sum
            from apps.accounts.models import AITokenUsage
            spend = (
                AITokenUsage.objects
                .filter(metadata__audit_id=str(audit.id))
                .aggregate(tokens=Sum("total_tokens"), cost=Sum("estimated_cost_usd"))
            )
            audit.total_tokens = int(spend["tokens"] or 0)
            audit.total_cost_usd = spend["cost"] or 0
        except Exception as exc:
            logger.warning("Cost roll-up failed for audit %s: %s", audit_id, exc)

        audit.status = LLMRankingAudit.STATUS_COMPLETED
        audit.overall_score = scores["overall_score"]
        audit.mention_rate = scores["mention_rate"]
        audit.avg_mention_rank = scores["avg_mention_rank"]
        audit.mention_rate_ci_lower = scores["mention_rate_ci_lower"]
        audit.mention_rate_ci_upper = scores["mention_rate_ci_upper"]
        audit.providers_queried = providers_succeeded
        audit.extraction_method = LLMRankingAudit.EXTRACTION_LLM
        audit.completed_at = timezone.now()
        # Calculate duration
        if audit.started_at:
            audit.duration_seconds = (audit.completed_at - audit.started_at).total_seconds()

        _audit_log(audit, f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        _audit_log(audit, f"🏁 AUDIT COMPLETE", "success")
        _audit_log(audit, f"   Overall Score: {scores['overall_score']}/100")
        _audit_log(audit, f"   Mention Rate: {scores['mention_rate']:.1f}%")
        _audit_log(audit, f"   Avg Rank When Mentioned: #{scores['avg_mention_rank']:.1f}")
        if audit.duration_seconds:
            _audit_log(audit, f"   Duration: {audit.duration_seconds:.1f}s")
        if audit.total_cost_usd:
            _audit_log(audit, f"   Cost: ${float(audit.total_cost_usd):.4f} ({audit.total_tokens:,} tokens)")
        _audit_log(audit, f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        audit.save(update_fields=[
            "status", "overall_score", "mention_rate", "avg_mention_rank",
            "mention_rate_ci_lower", "mention_rate_ci_upper",
            "providers_queried", "extraction_method", "completed_at",
            "duration_seconds", "total_tokens", "total_cost_usd", "updated_at",
        ])

        logger.info(
            "LLMRankingAudit %s completed: score=%d, mention_rate=%.1f%%",
            audit_id, scores["overall_score"], scores["mention_rate"],
        )


    # ── Recommendations ────────────────────────────────────────────────────

    @staticmethod
    def generate_recommendations(*, audit) -> list[str]:
        """
        Return actionable recommendations for improving LLM visibility
        based on the audit results — including a funnel-stage gap
        analysis (GEO playbook) when prompts are tagged.
        """
        recs = []
        results = list(audit.results.all())
        total = len(results)
        if not total:
            return ["Run the audit to see recommendations."]

        mention_rate = audit.mention_rate
        avg_rank = audit.avg_mention_rank
        score = audit.overall_score

        # ── Funnel-stage GEO playbook ─────────────────────────────────────
        # Bucket prompts by funnel_stage and compare visibility per stage.
        # The strategic gap (e.g. ranking on review queries but absent on
        # discovery queries) tells the user where to focus content + PR.
        from apps.llm_ranking.services.prompt_library import (
            INTENT_FUNNEL_STAGE as INTENT_TO_FUNNEL,
        )

        prompt_meta = {}
        for p in (audit.prompts or []):
            if isinstance(p, dict):
                text = (p.get("text") or "").strip().lower()
                stage = p.get("funnel_stage") or INTENT_TO_FUNNEL.get(p.get("type") or "", "niche")
                prompt_meta[text] = stage

        stage_stats: dict[str, dict] = {}
        for r in results:
            if not r.query_succeeded:
                continue
            stage = prompt_meta.get((r.prompt or "").strip().lower(), "niche")
            bucket = stage_stats.setdefault(stage, {"total": 0, "mentioned": 0})
            bucket["total"] += 1
            if r.is_mentioned:
                bucket["mentioned"] += 1

        def _rate(stage: str) -> float | None:
            b = stage_stats.get(stage)
            if not b or not b["total"]:
                return None
            return b["mentioned"] / b["total"] * 100

        bottom = _rate("bottom")
        mid = _rate("mid")
        top = _rate("top")

        # Bottom-of-funnel weakness is the biggest red flag — these are
        # the prompts your buyers actually run.
        if bottom is not None and bottom < 40:
            recs.append(
                f"You surface in only {bottom:.0f}% of bottom-of-funnel prompts "
                f"(direct discovery and brand-trust queries). This is the most "
                f"important gap — buyers running these prompts are ready to pick "
                f"a tool. Publish landing pages and product comparisons that "
                f"explicitly name {audit.business_name}, get listed in "
                f"third-party roundups (G2, Capterra, niche directories), and "
                f"earn backlinks from publications LLMs already crawl."
            )
        if (
            bottom is not None and top is not None
            and top - bottom >= 25
        ):
            recs.append(
                f"You score higher on awareness prompts ({top:.0f}%) than on "
                f"high-intent prompts ({bottom:.0f}%). Awareness without "
                f"discovery means buyers know the category but not your brand "
                f"in it — focus on bottom-funnel content and direct-comparison "
                f"pages, not more thought-leadership."
            )
        if (
            bottom is not None and mid is not None
            and mid - bottom >= 25
        ):
            recs.append(
                f"AI mentions you in comparison contexts ({mid:.0f}%) but not "
                f"in direct discovery ({bottom:.0f}%). This usually means "
                f"competitors own the category-defining content. Publish "
                f"definitive guides for your top use cases and lobby for "
                f"placement in industry listicles."
            )

        if mention_rate < 30:
            recs.append(
                "Your business is rarely mentioned by AI assistants. "
                "Publish detailed comparison articles, case studies, and feature pages "
                "so LLMs can discover and cite your content."
            )
        elif mention_rate < 60:
            recs.append(
                "You appear in some AI responses but not consistently. "
                "Create in-depth landing pages targeting your top keywords so "
                "LLMs have more authoritative content to reference."
            )

        if avg_rank and avg_rank > 3:
            recs.append(
                f"When mentioned, you rank around position {avg_rank:.0f}. "
                "Strengthen brand authority signals — get featured in industry "
                "roundups, directories, and third-party reviews that LLMs draw from."
            )

        # Check which providers are missing
        mentioned_providers = {r.provider for r in results if r.is_mentioned}
        all_providers = {r.provider for r in results if r.query_succeeded}
        missing = all_providers - mentioned_providers
        if missing:
            readable = {"claude": "Claude", "gpt4": "GPT-4", "gemini": "Gemini",
                        "perplexity": "Perplexity"}
            names = ", ".join(readable.get(p, p) for p in missing)
            recs.append(
                f"Your business does not appear in {names} responses. "
                "Ensure your website is indexed, has clear schema markup, "
                "and is referenced from high-authority domains."
            )

        negative_count = sum(1 for r in results if r.sentiment == "negative")
        if negative_count > 0:
            recs.append(
                f"{negative_count} AI response(s) mentioned your business with negative context. "
                "Review your public reputation — address negative reviews and "
                "publish positive case studies to shift the narrative."
            )

        if score >= 70:
            recs.append(
                "Strong LLM visibility. Maintain it by publishing fresh content regularly "
                "and monitoring your ranking monthly."
            )

        return recs or ["Good visibility! Keep publishing high-quality, indexed content."]
