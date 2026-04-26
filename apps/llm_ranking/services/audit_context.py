"""
Audit context generator — uses an LLM to produce real competitors
and topic suggestions from a scanned website's content.

Falls back to the scanned HTML body text if no LLM is available.
"""

import json
import logging
import re

from django.conf import settings

logger = logging.getLogger("apps")


def suggest_audit_context(
    *,
    business_name: str,
    description: str,
    industry: str,
    domain: str,
    content_summary: str = "",
) -> dict:
    """
    Use an LLM to generate real competitor names and ranking topics
    based on the business profile and scraped page content.

    Returns:
        {
            "topics": [str, ...],         # 8–12 real search topics
            "competitors": [              # 6–10 real competitors
                {"name": str, "domain": str},
                ...
            ]
        }
    """
    # Build a rich prompt using the actual page content
    context_block = ""
    if content_summary:
        context_block = f"\n\nHere is the actual content extracted from their website:\n{content_summary}\n"

    prompt = (
        f"I need you to analyze this business and return TWO things:\n\n"
        f"Business: {business_name}\n"
        f"Domain: {domain}\n"
        f"Industry: {industry}\n"
        f"Description: {description}\n"
        f"{context_block}\n"
        f"1. COMPETITORS: List 8–10 real companies that directly compete "
        f"with {business_name} in the {industry or 'same'} space. "
        f"For each, provide the company name and their actual website domain. "
        f"Only include REAL companies that actually exist.\n\n"
        f"2. TOPICS: Generate 8–12 realistic search queries that a buyer "
        f"would type into ChatGPT, Perplexity, or Claude when looking for "
        f"a product/service like {business_name}. These should be natural "
        f"questions based on what this business ACTUALLY offers (use the "
        f"website content above for accuracy). Examples: 'best [specific product] "
        f"tools for [specific use case]' or 'top alternatives to [competitor]'. "
        f"Make them highly specific to what this company actually sells.\n\n"
        f"Return ONLY valid JSON in this exact format, no other text:\n"
        f'{{"competitors": [{{"name": "Company", "domain": "company.com"}}], '
        f'"topics": ["search query 1", "search query 2"]}}'
    )

    # Try Anthropic (Claude) first
    result = _try_claude(prompt)
    if result:
        return result

    # Try OpenAI (GPT-4) as fallback
    result = _try_openai(prompt)
    if result:
        return result

    # Last resort: return empty (scanner already generates topics from DOM)
    logger.warning("No LLM available for audit context generation")
    return {"topics": [], "competitors": []}


def _parse_llm_response(text: str) -> dict | None:
    """Extract JSON from LLM response text."""
    try:
        # Try to find JSON object in the response
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            data = json.loads(match.group())
            topics = data.get("topics", [])
            competitors = data.get("competitors", [])
            # Validate structure
            if isinstance(topics, list) and isinstance(competitors, list):
                # Ensure competitors are dicts with name/domain
                clean_competitors = []
                for c in competitors:
                    if isinstance(c, dict) and c.get("name"):
                        clean_competitors.append({
                            "name": c["name"],
                            "domain": c.get("domain", ""),
                        })
                    elif isinstance(c, str):
                        clean_competitors.append({"name": c, "domain": ""})
                return {
                    "topics": [t for t in topics if isinstance(t, str)][:12],
                    "competitors": clean_competitors[:10],
                }
    except (json.JSONDecodeError, AttributeError) as e:
        logger.warning("Failed to parse LLM response: %s", e)
    return None


def _try_claude(prompt: str) -> dict | None:
    """Try generating context via Claude."""
    api_key = getattr(settings, "ANTHROPIC_API_KEY", "")
    if not api_key:
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        try:
            from core.ai_tracking import record_usage
            record_usage(
                module="llm_ranking",
                model_name="claude-sonnet-4-20250514",
                input_tokens=resp.usage.input_tokens,
                output_tokens=resp.usage.output_tokens,
                metadata={"role": "context_inference"},
            )
        except Exception:
            pass
        return _parse_llm_response(resp.content[0].text)
    except Exception as e:
        logger.warning("Claude audit context failed: %s", e)
        return None


def _try_openai(prompt: str) -> dict | None:
    """Try generating context via OpenAI."""
    api_key = getattr(settings, "OPENAI_API_KEY", "")
    if not api_key:
        return None
    try:
        import openai
        client = openai.OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        try:
            from core.ai_tracking import record_usage
            usage = getattr(resp, "usage", None)
            if usage:
                record_usage(
                    module="llm_ranking",
                    model_name="gpt-4o-mini",
                    input_tokens=getattr(usage, "prompt_tokens", 0),
                    output_tokens=getattr(usage, "completion_tokens", 0),
                    metadata={"role": "context_inference"},
                )
        except Exception:
            pass
        return _parse_llm_response(resp.choices[0].message.content)
    except Exception as e:
        logger.warning("OpenAI audit context failed: %s", e)
        return None
