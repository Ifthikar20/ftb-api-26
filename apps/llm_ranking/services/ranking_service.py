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


class LLMRankingService:

    # ── Prompt generation ──────────────────────────────────────────────────

    @staticmethod
    def generate_prompts(*, business_name: str, industry: str, description: str,
                         keywords: list, use_case: str = "",
                         location: str = "",
                         themes: list | None = None) -> list[dict]:
        """
        Generate discovery prompts from business context.

        Returns a list of dicts: [{"text": str, "type": str}, ...]
        where type is the intent tag (recommendation, comparison, etc.).

        Uses the intent-balanced PromptLibrary for the deterministic base set,
        then asks Claude for additional natural-language variants to cover
        phrasings the library can't anticipate.
        """
        from apps.llm_ranking.services.prompt_library import PromptLibrary

        use_case = use_case or (keywords[0] if keywords else industry)

        # Library returns intent-tagged dicts: {"text": ..., "intent": ...}
        base_items = PromptLibrary.generate(
            industry=industry or "software",
            use_case=use_case,
            location=location,
            max_prompts=10,
            themes=themes,
        )
        # Normalise to {"text": str, "type": str}
        result_items = [{"text": p["text"], "type": p["intent"]} for p in base_items]

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
            # Track token usage
            try:
                from core.ai_tracking import record_usage
                record_usage(
                    module="llm_ranking", model_name="claude-sonnet-4-20250514",
                    input_tokens=resp.usage.input_tokens, output_tokens=resp.usage.output_tokens,
                )
            except Exception:
                pass
            match = _re.search(r"\[.*\]", text, _re.DOTALL)
            if match:
                ai_prompts = json.loads(match.group())
                for p in ai_prompts:
                    if isinstance(p, str):
                        result_items.append({"text": p.strip(), "type": "custom"})
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

    @staticmethod
    def _query_claude(prompt: str) -> tuple[bool, str, str]:
        """
        Returns (succeeded, response_text, error_message).
        """
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            resp = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=SYSTEM_INSTRUCTION,
                messages=[{"role": "user", "content": prompt}],
            )
            # Track token usage
            try:
                from core.ai_tracking import record_usage
                record_usage(
                    module="llm_ranking", model_name="claude-sonnet-4-20250514",
                    input_tokens=resp.usage.input_tokens, output_tokens=resp.usage.output_tokens,
                )
            except Exception:
                pass
            return True, resp.content[0].text.strip(), ""
        except Exception as e:
            return False, "", str(e)

    @staticmethod
    def _query_openai(prompt: str) -> tuple[bool, str, str]:
        """Query GPT-4 via OpenAI API."""
        api_key = getattr(settings, "OPENAI_API_KEY", "")
        if not api_key:
            return False, "", "OPENAI_API_KEY not configured"
        try:
            import openai
            client = openai.OpenAI(api_key=api_key)
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                max_tokens=1024,
                messages=[
                    {"role": "system", "content": SYSTEM_INSTRUCTION},
                    {"role": "user", "content": prompt},
                ],
            )
            return True, resp.choices[0].message.content.strip(), ""
        except Exception as e:
            return False, "", str(e)

    @staticmethod
    def _query_gemini(prompt: str) -> tuple[bool, str, str]:
        """Query Gemini via Google Generative AI SDK."""
        api_key = getattr(settings, "GEMINI_API_KEY", "")
        if not api_key:
            return False, "", "GEMINI_API_KEY not configured"
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            full_prompt = f"{SYSTEM_INSTRUCTION}\n\n{prompt}"
            resp = model.generate_content(full_prompt)
            return True, resp.text.strip(), ""
        except Exception as e:
            return False, "", str(e)

    @staticmethod
    def _query_perplexity(prompt: str) -> tuple[bool, str, str]:
        """Query Perplexity via their OpenAI-compatible API."""
        api_key = getattr(settings, "PERPLEXITY_API_KEY", "")
        if not api_key:
            return False, "", "PERPLEXITY_API_KEY not configured"
        try:
            import requests
            resp = requests.post(
                "https://api.perplexity.ai/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "llama-3.1-sonar-small-128k-online",
                    "messages": [
                        {"role": "system", "content": SYSTEM_INSTRUCTION},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 1024,
                },
                timeout=30,
            )
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"].strip()
            return True, text, ""
        except Exception as e:
            return False, "", str(e)

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

    # ── Main audit runner ──────────────────────────────────────────────────

    @staticmethod
    def run_audit(*, audit_id: str) -> None:
        """
        Execute a full LLM ranking audit. Called as a Celery task.
        Updates the audit record with results and computed scores.
        Saves progress after each query so the frontend can show ETA.
        """
        from apps.llm_ranking.models import LLMRankingAudit, LLMRankingResult

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

        # Calculate total queries and set progress tracking
        # Prompts may be structured [{"text": ..., "type": ...}] or flat ["..."]
        prompt_items = []
        for p in audit.prompts:
            if isinstance(p, dict):
                prompt_items.append({"text": p.get("text", ""), "type": p.get("type", "custom")})
            else:
                prompt_items.append({"text": str(p), "type": "custom"})

        total = len(selected_providers) * len(prompt_items)
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

        for provider in selected_providers:
            query_fn = provider_map.get(provider)
            if not query_fn:
                continue

            for prompt_item in prompt_items:
                prompt_text = prompt_item["text"]
                prompt_type = prompt_item["type"]
                try:
                    succeeded, response_text, error = query_fn(prompt_text)
                except Exception as exc:
                    succeeded, response_text, error = False, "", str(exc)
                    logger.warning("Provider %s threw for audit %s: %s", provider, audit_id, exc)

                if succeeded:
                    from apps.llm_ranking.services.extraction_service import (
                        HaikuExtractionService,
                    )
                    analysis = HaikuExtractionService.extract(
                        response_text=response_text,
                        brand_name=audit.business_name,
                        keywords=audit.keywords,
                    )
                else:
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
                    prompt_type=prompt_type,
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

            if any(r.provider == provider and r.query_succeeded for r in all_results):
                providers_succeeded.append(provider)

        # Compute aggregate scores
        scores = LLMRankingService.compute_overall_score(all_results)

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
        audit.save(update_fields=[
            "status", "overall_score", "mention_rate", "avg_mention_rank",
            "mention_rate_ci_lower", "mention_rate_ci_upper",
            "providers_queried", "extraction_method", "completed_at",
            "duration_seconds", "updated_at",
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
        based on the audit results.
        """
        recs = []
        results = list(audit.results.all())
        total = len(results)
        if not total:
            return ["Run the audit to see recommendations."]

        mention_rate = audit.mention_rate
        avg_rank = audit.avg_mention_rank
        score = audit.overall_score

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
