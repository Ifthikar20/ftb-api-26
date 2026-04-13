"""
AI-powered lead discovery service.
Routes through OpenClaw AI agent when available (self-hosted),
otherwise falls back to Claude + Google Custom Search pipeline.
"""
import json
import logging
import re

import requests
from django.conf import settings

logger = logging.getLogger("apps")


def google_search_configured() -> bool:
    """Return True if Google Custom Search API credentials are present."""
    return bool(
        getattr(settings, "GOOGLE_SEARCH_API_KEY", "")
        and getattr(settings, "GOOGLE_SEARCH_ENGINE_ID", "")
    )

GOOGLE_SEARCH_URL = "https://www.googleapis.com/customsearch/v1"


class AILeadFinder:
    """Find potential leads via AI prompt + social profile search."""

    # ── 1. Parse prompt into search criteria via Claude ──
    @staticmethod
    def _parse_prompt(prompt: str) -> dict:
        """Use Claude to extract structured criteria from a natural-language prompt."""
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            resp = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=512,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "Extract structured lead search criteria from this prompt. "
                            "Return ONLY valid JSON with these fields:\n"
                            '{"role":"...", "industry":"...", "location":"...", '
                            '"keywords":["..."], "company_size":"...", "seniority":"..."}\n'
                            "Leave fields empty string or empty list if not mentioned.\n\n"
                            f"Prompt: {prompt}"
                        ),
                    }
                ],
            )
            text = resp.content[0].text.strip()
            # Track token usage
            try:
                from core.ai_tracking import record_usage
                record_usage(
                    module="lead_finder", model_name="claude-sonnet-4-20250514",
                    input_tokens=resp.usage.input_tokens, output_tokens=resp.usage.output_tokens,
                )
            except Exception:
                pass
            # Extract JSON from potential markdown code blocks
            json_match = re.search(r"\{.*\}", text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            logger.warning("Claude parse failed: %s", e)
        return {"role": "", "industry": "", "location": "", "keywords": [], "company_size": "", "seniority": ""}

    # ── 2. Search Google for LinkedIn/Twitter profiles ──
    @staticmethod
    def _google_search(query: str, site: str, num: int = 5) -> list:
        """Search Google Custom Search API for profiles on a specific site."""
        api_key = getattr(settings, "GOOGLE_SEARCH_API_KEY", "")
        engine_id = getattr(settings, "GOOGLE_SEARCH_ENGINE_ID", "")
        if not api_key or not engine_id:
            logger.warning(
                "Google Custom Search not configured — set GOOGLE_SEARCH_API_KEY "
                "and GOOGLE_SEARCH_ENGINE_ID for real profile search results."
            )
            return []

        try:
            resp = requests.get(
                GOOGLE_SEARCH_URL,
                params={
                    "key": api_key,
                    "cx": engine_id,
                    "q": f"site:{site} {query}",
                    "num": num,
                },
                timeout=10,
            )
            data = resp.json()

            # Check for API errors (403 = API not enabled, 400 = bad key, etc.)
            if resp.status_code != 200:
                error_msg = data.get("error", {}).get("message", resp.text[:200])
                logger.error(
                    "Google Custom Search API error (HTTP %d): %s",
                    resp.status_code,
                    error_msg,
                )
                return []

            results = []
            for item in data.get("items", []):
                results.append({
                    "title": item.get("title", ""),
                    "link": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                })
            return results
        except Exception as e:
            logger.warning("Google search failed: %s", e)
            return []

    # ── 3. Use Claude to generate lead suggestions (fallback or enrichment) ──
    @staticmethod
    def _ai_generate_leads(prompt: str, criteria: dict, search_results: list) -> list:
        """Use Claude to score search results or generate suggestions."""
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

            context = ""
            if search_results:
                context = "Here are search results from LinkedIn and Twitter:\n"
                for r in search_results:
                    context += f"- {r['title']} | {r['link']} | {r['snippet']}\n"
                context += "\nParse these into structured lead profiles and score them.\n"
            else:
                context = (
                    "No search results were available. Based on the criteria, suggest "
                    "realistic lead profiles that would typically match this search. "
                    "These are AI-generated suggestions to guide outreach — not verified contacts. "
                    "Set is_from_search to false and is_ai_suggested to true for all leads.\n"
                )

            resp = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"Original request: {prompt}\n"
                            f"Parsed criteria: {json.dumps(criteria)}\n\n"
                            f"{context}\n"
                            "Return a JSON array of lead objects. Each object:\n"
                            "{\n"
                            '  "name": "Full Name",\n'
                            '  "title": "Job Title",\n'
                            '  "company": "Company Name",\n'
                            '  "company_url": "https://company-website.com",\n'
                            '  "email": "realistic professional email based on name and company domain",\n'
                            '  "phone": "realistic phone number with area code, or empty string if unknown",\n'
                            '  "location": "City, State/Country",\n'
                            '  "linkedin_url": "https://linkedin.com/in/...",\n'
                            '  "twitter_url": "https://twitter.com/...",\n'
                            '  "relevance_score": 85,\n'
                            '  "reason": "Why this person is a good lead",\n'
                            '  "industry": "Industry",\n'
                            '  "is_from_search": true/false\n'
                            "}\n"
                            "Return 8-15 leads sorted by relevance_score descending. "
                            "Return ONLY the JSON array, no other text."
                        ),
                    }
                ],
            )
            text = resp.content[0].text.strip()
            # Track token usage
            try:
                from core.ai_tracking import record_usage
                record_usage(
                    module="lead_finder", model_name="claude-sonnet-4-20250514",
                    input_tokens=resp.usage.input_tokens, output_tokens=resp.usage.output_tokens,
                )
            except Exception:
                pass
            # Extract JSON array
            json_match = re.search(r"\[.*\]", text, re.DOTALL)
            if json_match:
                leads = json.loads(json_match.group())
                # Ensure scores are ints
                for lead in leads:
                    lead["relevance_score"] = int(lead.get("relevance_score", 50))
                    lead["is_from_search"] = bool(lead.get("is_from_search", False))
                return sorted(leads, key=lambda x: x["relevance_score"], reverse=True)
        except Exception as e:
            logger.error("Claude lead generation failed: %s", e)
        return []

    # ── Public API ──
    @classmethod
    def search(cls, prompt: str) -> dict:
        """
        Full pipeline:
        1. Try OpenClaw agent (real X/LinkedIn scraping) if available
        2. Fallback: parse prompt with Claude → Google search → Claude scoring
        """
        # ── Strategy 1: OpenClaw AI Agent ──
        try:
            from apps.leads.services.openclaw_service import OpenClawService

            openclaw_result = OpenClawService.send_prompt(prompt)
            if openclaw_result and openclaw_result.get("leads"):
                leads = openclaw_result["leads"]
                sources = openclaw_result.get("sources_searched", {})
                logger.info(
                    "OpenClaw returned %d leads (x:%d, li:%d, web:%d)",
                    len(leads),
                    sources.get("x", 0),
                    sources.get("linkedin", 0),
                    sources.get("web", 0),
                )
                return {
                    "criteria": openclaw_result.get("criteria", {}),
                    "leads": leads,
                    "sources_searched": {
                        "linkedin": sources.get("linkedin", 0),
                        "twitter": sources.get("x", 0),
                        "web": sources.get("web", 0),
                    },
                    "total": len(leads),
                    "has_google_search": True,
                    "engine": "openclaw",
                }
        except Exception as e:
            logger.warning("OpenClaw integration failed, using fallback: %s", e)

        # ── Strategy 2: Claude + Google Custom Search (fallback) ──
        logger.info("Using Claude fallback for lead search")

        # Step 1: Parse prompt
        criteria = cls._parse_prompt(prompt)
        logger.info("AI Lead Finder criteria: %s", criteria)

        # Step 2: Build search query from criteria
        query_parts = []
        if criteria.get("role"):
            query_parts.append(criteria["role"])
        if criteria.get("industry"):
            query_parts.append(criteria["industry"])
        if criteria.get("location"):
            query_parts.append(criteria["location"])
        for kw in criteria.get("keywords", []):
            query_parts.append(kw)
        search_query = " ".join(query_parts) if query_parts else prompt

        # Step 3: Search LinkedIn and Twitter
        linkedin_results = cls._google_search(search_query, "linkedin.com/in", num=5)
        twitter_results = cls._google_search(search_query, "twitter.com", num=5)
        all_results = linkedin_results + twitter_results

        # Step 4: Use AI to score/generate leads
        leads = cls._ai_generate_leads(prompt, criteria, all_results)

        return {
            "criteria": criteria,
            "leads": leads,
            "sources_searched": {
                "linkedin": len(linkedin_results),
                "twitter": len(twitter_results),
            },
            "total": len(leads),
            "has_google_search": bool(
                getattr(settings, "GOOGLE_SEARCH_API_KEY", "")
                and getattr(settings, "GOOGLE_SEARCH_ENGINE_ID", "")
            ),
            "engine": "claude",
        }
