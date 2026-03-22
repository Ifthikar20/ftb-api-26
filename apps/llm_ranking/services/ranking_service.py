"""
LLM Ranking Service — Generative Engine Optimization (GEO) audit.

Queries Claude, GPT-4, Gemini, and Perplexity with discovery prompts
and measures how prominently the business appears in AI-generated answers.
"""
import logging
import re

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger("apps")

# Providers and human labels
PROVIDERS = ["claude", "gpt4", "gemini", "perplexity"]

# Default prompt templates. {industry}, {description}, {keywords} are interpolated.
DEFAULT_PROMPT_TEMPLATES = [
    "What are the best {industry} tools available right now?",
    "Can you recommend a {industry} platform that helps with {use_case}?",
    "I'm looking for {industry} software. What are the top options?",
    "Which {industry} solutions do most companies use?",
    "If I need to {use_case}, what tools should I consider?",
    "What are the leading {industry} products recommended by experts?",
]


class LLMRankingService:

    # ── Prompt generation ──────────────────────────────────────────────────

    @staticmethod
    def generate_prompts(*, business_name: str, industry: str, description: str,
                         keywords: list, use_case: str = "") -> list[str]:
        """
        Generate discovery prompts from business context.
        Uses Claude to produce additional natural-language variants.
        """
        use_case = use_case or (keywords[0] if keywords else industry)
        base_prompts = [
            t.format(industry=industry or "software", use_case=use_case)
            for t in DEFAULT_PROMPT_TEMPLATES
        ]

        # Use Claude to generate additional natural variants
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
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
                        f"Keywords: {', '.join(keywords)}\n\n"
                        "Return ONLY a JSON array of 4 question strings, no other text."
                    ),
                }],
            )
            import json
            import re as _re
            text = resp.content[0].text.strip()
            match = _re.search(r"\[.*\]", text, _re.DOTALL)
            if match:
                ai_prompts = json.loads(match.group())
                base_prompts += [p for p in ai_prompts if isinstance(p, str)]
        except Exception as e:
            logger.warning("Prompt generation via Claude failed: %s", e)

        # Deduplicate while preserving order
        seen = set()
        result = []
        for p in base_prompts:
            key = p.strip().lower()
            if key not in seen:
                seen.add(key)
                result.append(p.strip())
        return result[:10]  # cap at 10 prompts per audit

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
                messages=[{"role": "user", "content": prompt}],
            )
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
                messages=[{"role": "user", "content": prompt}],
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
            resp = model.generate_content(prompt)
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
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1024,
                },
                timeout=20,
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

        Returns a dict with:
          is_mentioned, mention_rank, sentiment, confidence_score, mention_context
        """
        text_lower = response_text.lower()
        name_lower = business_name.lower()

        # Build search terms: business name + keywords
        search_terms = [name_lower] + [k.lower() for k in keywords if k]

        is_mentioned = any(term in text_lower for term in search_terms if term)
        if not is_mentioned:
            return {
                "is_mentioned": False,
                "mention_rank": None,
                "sentiment": "not_mentioned",
                "confidence_score": 95.0,
                "mention_context": "",
            }

        # Estimate rank by finding position among numbered/bulleted list items
        lines = response_text.split("\n")
        rank = None
        context = ""
        item_index = 0
        for line in lines:
            line_stripped = line.strip()
            # Count list items (numbered or bulleted)
            if re.match(r"^(\d+[\.\)]|[-*•])\s+", line_stripped):
                item_index += 1
                if any(term in line_stripped.lower() for term in search_terms if term):
                    rank = item_index
                    context = line_stripped[:300]
                    break
            elif any(term in line_stripped.lower() for term in search_terms if term) and not context:
                context = line_stripped[:300]

        # Sentiment analysis using simple heuristics + Claude
        sentiment = LLMRankingService._classify_sentiment(
            context=context or response_text[:500],
            business_name=business_name,
        )

        confidence = 90.0 if rank is not None else 70.0
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
        ]
        negative_signals = [
            "avoid", "poor", "bad", "expensive", "difficult", "limited",
            "unreliable", "not recommended", "worse",
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

        Returns dict with overall_score, mention_rate, avg_mention_rank.
        """
        total = len(results)
        if not total:
            return {"overall_score": 0, "mention_rate": 0.0, "avg_mention_rank": 0.0}

        succeeded = [r for r in results if r.query_succeeded]
        mentioned = [r for r in succeeded if r.is_mentioned]
        mention_rate = len(mentioned) / len(succeeded) * 100 if succeeded else 0.0

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
        }

    # ── Main audit runner ──────────────────────────────────────────────────

    @staticmethod
    def run_audit(*, audit_id: str) -> None:
        """
        Execute a full LLM ranking audit. Called as a Celery task.
        Updates the audit record with results and computed scores.
        """
        from apps.llm_ranking.models import LLMRankingAudit, LLMRankingResult

        try:
            audit = LLMRankingAudit.objects.select_related("website").get(id=audit_id)
        except LLMRankingAudit.DoesNotExist:
            logger.error("LLMRankingAudit %s not found", audit_id)
            return

        audit.status = LLMRankingAudit.STATUS_RUNNING
        audit.save(update_fields=["status", "updated_at"])

        provider_map = {
            LLMRankingResult.PROVIDER_CLAUDE: LLMRankingService._query_claude,
            LLMRankingResult.PROVIDER_GPT4: LLMRankingService._query_openai,
            LLMRankingResult.PROVIDER_GEMINI: LLMRankingService._query_gemini,
            LLMRankingResult.PROVIDER_PERPLEXITY: LLMRankingService._query_perplexity,
        }

        all_results = []
        providers_queried = []

        for provider, query_fn in provider_map.items():
            for prompt in audit.prompts:
                succeeded, response_text, error = query_fn(prompt)
                analysis = (
                    LLMRankingService._analyze_mention(
                        response_text=response_text,
                        business_name=audit.business_name,
                        keywords=audit.keywords,
                    )
                    if succeeded
                    else {
                        "is_mentioned": False,
                        "mention_rank": None,
                        "sentiment": LLMRankingResult.SENTIMENT_NOT_MENTIONED,
                        "confidence_score": 0.0,
                        "mention_context": "",
                    }
                )

                result = LLMRankingResult.objects.create(
                    audit=audit,
                    provider=provider,
                    prompt=prompt,
                    response_text=response_text,
                    is_mentioned=analysis["is_mentioned"],
                    mention_rank=analysis["mention_rank"],
                    sentiment=analysis["sentiment"],
                    confidence_score=analysis["confidence_score"],
                    mention_context=analysis["mention_context"],
                    query_succeeded=succeeded,
                    error_message=error,
                )
                all_results.append(result)

            if any(r.provider == provider and r.query_succeeded for r in all_results):
                providers_queried.append(provider)

        # Compute aggregate scores
        scores = LLMRankingService.compute_overall_score(all_results)

        audit.status = LLMRankingAudit.STATUS_COMPLETED
        audit.overall_score = scores["overall_score"]
        audit.mention_rate = scores["mention_rate"]
        audit.avg_mention_rank = scores["avg_mention_rank"]
        audit.providers_queried = providers_queried
        audit.completed_at = timezone.now()
        audit.save(update_fields=[
            "status", "overall_score", "mention_rate", "avg_mention_rank",
            "providers_queried", "completed_at", "updated_at",
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
