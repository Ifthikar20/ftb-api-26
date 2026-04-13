"""
Agent Tool Registry
───────────────────
Maps tool names → callables that agents can invoke.
Each tool wraps an existing service so we reuse all current business logic.
"""
import logging

logger = logging.getLogger("apps.agents")


# ──────────────────────────────────────────────
# Tool definitions (name, description, callable)
# ──────────────────────────────────────────────

def _get_analytics_overview(*, website_id: str, period: str = "7d") -> dict:
    """Get analytics overview for a website."""
    from apps.analytics.services.analytics_service import AnalyticsService
    return AnalyticsService.get_overview(website_id=website_id, period=period)


def _get_top_pages(*, website_id: str, period: str = "7d", limit: int = 10) -> list:
    """Get top pages by pageviews."""
    from apps.analytics.services.analytics_service import AnalyticsService
    return AnalyticsService.get_top_pages(website_id=website_id, period=period, limit=limit)


def _get_keyword_scores(*, website_id: str) -> list:
    """Get AI-scored keywords for a website."""
    from apps.analytics.services.keyword_intelligence_service import KeywordIntelligenceService
    return KeywordIntelligenceService.get_scored_keywords(website_id=website_id)


def _get_trending_keywords(*, website_id: str) -> dict:
    """Get trending keywords from Google Trends relevant to the website."""
    from apps.analytics.services.keyword_intelligence_service import KeywordIntelligenceService
    return KeywordIntelligenceService.get_trending(website_id=website_id)


def _get_ai_insights(*, website_id: str) -> list:
    """Get AI-generated insights for a website."""
    from apps.analytics.services.ai_insights_service import AIInsightsService
    return AIInsightsService.generate_insights(website_id=website_id)


def _get_competitor_changes(*, website_id: str) -> list:
    """Get recent competitor changes."""
    from apps.competitors.models import Competitor
    from apps.competitors.services.change_detection_service import ChangeDetectionService
    changes = []
    for comp in Competitor.objects.filter(website_id=website_id):
        try:
            comp_changes = ChangeDetectionService.detect_changes(competitor=comp)
            changes.extend([
                {"competitor": comp.name, "type": c.change_type, "detail": c.detail}
                for c in comp_changes
            ])
        except Exception as e:
            logger.warning(f"Change detection failed for {comp.id}: {e}")
    return changes


def _get_keyword_gaps(*, website_id: str) -> list:
    """Get keyword gap analysis vs competitors."""
    from apps.competitors.services.comparison_service import ComparisonService
    return ComparisonService.find_keyword_gaps(website_id=website_id)


def _get_lead_summary(*, website_id: str) -> dict:
    """Get a summary of current leads and scoring."""
    from apps.leads.models import Lead
    leads = Lead.objects.filter(website_id=website_id)
    total = leads.count()
    hot = leads.filter(score__gte=70).count()
    warm = leads.filter(score__gte=30, score__lt=70).count()
    return {"total": total, "hot": hot, "warm": warm, "cold": total - hot - warm}


def _generate_content_brief(*, website_id: str, keyword: str, target_audience: str = "") -> dict:
    """Generate a content brief for a specific keyword."""
    import anthropic
    from django.conf import settings

    from apps.websites.models import Website

    website = Website.objects.get(id=website_id)
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=800,
        messages=[{
            "role": "user",
            "content": (
                f"Generate a content brief for {website.name} ({website.url}) "
                f"targeting the keyword: '{keyword}'. "
                f"Target audience: {target_audience or website.industry or 'general'}. "
                "Return JSON with: title, outline (list of sections), "
                "target_word_count, key_points (list), seo_tips (list). "
                "Return ONLY valid JSON."
            ),
        }],
    )

    import json
    try:
        return json.loads(response.content[0].text)
    except Exception:
        return {"title": f"Content for '{keyword}'", "outline": [], "key_points": []}


# ── SEO Keyword Optimizer Tools ──────────────────────────────────────────────


def _scan_website_keywords(*, website_id: str) -> dict:
    """Run a full DOM keyword scan on the website and return extracted keywords,
    density data, trend data, score breakdown, and synonym suggestions."""
    import hashlib

    from django.core.cache import cache

    from apps.analytics.services.seo_keyword_scanner import SEOKeywordScanner
    from apps.websites.models import Website

    website = Website.objects.get(id=website_id)

    # Clear cache to force a fresh crawl
    cache_key = f"seo_scan_{hashlib.md5(website.url.encode()).hexdigest()}"
    cache.delete(cache_key)

    result = SEOKeywordScanner.scan(website_url=website.url, website_id=str(website.id))

    if result.get("error"):
        return {"error": result["error"]}

    # Return a meaningful summary the agent can reason about
    return {
        "url": result.get("url"),
        "pages_scanned": result.get("pages_scanned", 0),
        "score": result.get("score", 0),
        "score_breakdown": result.get("score_breakdown", {}),
        "keywords": result.get("keywords", []),
        "trends": result.get("trends", {}),
        "suggestions": result.get("suggestions", []),
        "page_meta": result.get("page_meta", {}),
        "geo_data": result.get("geo_data", {}),
    }


def _check_ai_visibility(*, website_id: str) -> dict:
    """Check how visible the website is across AI engines (Claude, ChatGPT,
    Perplexity) for its top keywords. Returns per-engine visibility scores."""
    import hashlib
    from urllib.parse import urlparse

    from django.core.cache import cache

    from apps.analytics.services.seo_keyword_scanner import SEOKeywordScanner
    from apps.websites.models import Website

    website = Website.objects.get(id=website_id)
    parsed = urlparse(website.url)
    domain = parsed.netloc.replace("www.", "")

    # Get the latest scan data
    cache_key = f"seo_scan_{hashlib.md5(website.url.encode()).hexdigest()}"
    scan_data = cache.get(cache_key) or {}

    keywords = [k["keyword"] for k in scan_data.get("keywords", [])[:6]]
    if not keywords:
        return {"error": "No scan data found. Run scan_website_keywords first."}

    try:
        ai_rankings = SEOKeywordScanner._check_ai_rankings(keywords, domain)
        return {
            "domain": domain,
            "keywords_checked": keywords,
            "engines": ai_rankings,
            "overall_score": ai_rankings.get("overall_score", 0),
        }
    except Exception as e:
        logger.warning(f"AI visibility check failed: {e}")
        return {"error": str(e), "domain": domain, "keywords_checked": keywords}


def _update_seo_rules(*, website_id: str, optimized_title: str = "",
                       optimized_description: str = "",
                       focus_keywords: str = "",
                       schema_type: str = "WebSite",
                       og_title: str = "", og_description: str = "") -> dict:
    """Update the Dynamic SEO Optimizer rules for the website based on the
    agent's analysis. This changes what the live seo-rules/ endpoint serves,
    which is consumed by the FetchBot script on the user's site.

    Only updates fields that are provided (non-empty)."""
    import hashlib
    from urllib.parse import urlparse

    from django.core.cache import cache

    from apps.websites.models import Website

    website = Website.objects.get(id=website_id)
    parsed = urlparse(website.url)
    site_name = parsed.netloc.replace("www.", "").split(".")[0].title()

    # Load existing rules or build fresh
    rules_cache_key = f"seo_rules_{website_id}"
    rules = cache.get(rules_cache_key) or {"global": {}, "pages": {}}

    # Update global rules
    if "global" not in rules:
        rules["global"] = {}

    # Schema
    rules["global"]["schema"] = {
        "@context": "https://schema.org",
        "@type": schema_type or "WebSite",
        "name": site_name,
        "url": website.url,
    }
    if focus_keywords:
        rules["global"]["schema"]["keywords"] = focus_keywords

    # Canonical
    rules["global"]["canonical"] = website.url.rstrip("/") + "{path}"

    # Open Graph
    og = rules["global"].get("og", {})
    og["type"] = "website"
    og["site_name"] = site_name
    og["url"] = website.url
    if og_title:
        og["title"] = og_title
    if og_description:
        og["description"] = og_description
    rules["global"]["og"] = og

    # Homepage page rules
    page_rules = rules.get("pages", {}).get("/", {})
    if optimized_title:
        page_rules["title"] = optimized_title
    if optimized_description:
        page_rules["description"] = optimized_description
    if optimized_title:
        page_rules.setdefault("og", {})["title"] = optimized_title
    if optimized_description:
        page_rules.setdefault("og", {})["description"] = optimized_description

    if page_rules:
        rules.setdefault("pages", {})["/"] = page_rules

    # Hreflang defaults if not present
    if "hreflang" not in rules["global"]:
        rules["global"]["hreflang"] = [
            {"lang": "en", "href": website.url},
            {"lang": "x-default", "href": website.url},
        ]

    # Geo defaults
    if "geo" not in rules["global"]:
        rules["global"]["geo"] = {"region": "US"}

    # Save to cache (10 min — will be refreshed on next scan)
    cache.set(rules_cache_key, rules, 600)

    # Build a summary of what was applied
    changes_applied = []
    if optimized_title:
        changes_applied.append(f"Title → '{optimized_title}'")
    if optimized_description:
        changes_applied.append(f"Meta description → '{optimized_description[:60]}...'")
    if focus_keywords:
        changes_applied.append(f"Schema keywords → '{focus_keywords}'")
    if og_title:
        changes_applied.append(f"OG title → '{og_title}'")
    if og_description:
        changes_applied.append(f"OG description → '{og_description[:60]}...'")
    changes_applied.append("Hreflang tags ensured")
    changes_applied.append("Geo region tag ensured")

    return {
        "success": True,
        "website": website.url,
        "changes_applied": changes_applied,
        "rules_cached_for": "10 minutes (auto-refreshes on next scan)",
    }


# ──────────────────────────────────────────────
# Tool Registry
# ──────────────────────────────────────────────

TOOL_REGISTRY = {
    "get_analytics_overview": {
        "fn": _get_analytics_overview,
        "description": "Get website analytics overview (visitors, pageviews, bounce rate, sources, etc.)",
        "params": {
            "website_id": {"type": "string", "required": True, "description": "Website UUID"},
            "period": {"type": "string", "required": False, "description": "Period: 24h, 7d, 30d, 90d"},
        },
    },
    "get_top_pages": {
        "fn": _get_top_pages,
        "description": "Get top pages by pageviews for a website",
        "params": {
            "website_id": {"type": "string", "required": True},
            "period": {"type": "string", "required": False},
            "limit": {"type": "integer", "required": False},
        },
    },
    "get_keyword_scores": {
        "fn": _get_keyword_scores,
        "description": "Get AI-scored keywords with rankings, volume, difficulty, and opportunity score",
        "params": {"website_id": {"type": "string", "required": True}},
    },
    "get_trending_keywords": {
        "fn": _get_trending_keywords,
        "description": "Get trending keywords from Google Trends relevant to the website's niche",
        "params": {"website_id": {"type": "string", "required": True}},
    },
    "get_ai_insights": {
        "fn": _get_ai_insights,
        "description": "Get AI-generated insights (anomalies, opportunities, warnings) for a website",
        "params": {"website_id": {"type": "string", "required": True}},
    },
    "get_competitor_changes": {
        "fn": _get_competitor_changes,
        "description": "Get recent changes detected across all tracked competitors",
        "params": {"website_id": {"type": "string", "required": True}},
    },
    "get_keyword_gaps": {
        "fn": _get_keyword_gaps,
        "description": "Find keywords your competitors rank for but you don't",
        "params": {"website_id": {"type": "string", "required": True}},
    },
    "get_lead_summary": {
        "fn": _get_lead_summary,
        "description": "Get a summary of lead counts and scoring (hot/warm/cold)",
        "params": {"website_id": {"type": "string", "required": True}},
    },
    "generate_content_brief": {
        "fn": _generate_content_brief,
        "description": "Generate a detailed content brief for a target keyword",
        "params": {
            "website_id": {"type": "string", "required": True},
            "keyword": {"type": "string", "required": True},
            "target_audience": {"type": "string", "required": False},
        },
    },
    "scan_website_keywords": {
        "fn": _scan_website_keywords,
        "description": "Crawl the website DOM and extract all keywords with density, locations, trends, score breakdown, and synonym suggestions",
        "params": {"website_id": {"type": "string", "required": True}},
    },
    "check_ai_visibility": {
        "fn": _check_ai_visibility,
        "description": "Check if Claude, ChatGPT, and Perplexity recommend this domain when asked about its keywords. Returns per-engine visibility scores",
        "params": {"website_id": {"type": "string", "required": True}},
    },
    "update_seo_rules": {
        "fn": _update_seo_rules,
        "description": "Update the live Dynamic SEO Optimizer rules (title, meta description, schema, Open Graph) based on keyword analysis. Changes are served by the FetchBot script on the user's site",
        "params": {
            "website_id": {"type": "string", "required": True},
            "optimized_title": {"type": "string", "required": False, "description": "Optimized page title incorporating top keywords"},
            "optimized_description": {"type": "string", "required": False, "description": "Optimized meta description with keyword coverage"},
            "focus_keywords": {"type": "string", "required": False, "description": "Comma-separated list of focus keywords for schema markup"},
            "schema_type": {"type": "string", "required": False, "description": "Schema.org type (WebSite, Organization, etc.)"},
            "og_title": {"type": "string", "required": False, "description": "Optimized Open Graph title"},
            "og_description": {"type": "string", "required": False, "description": "Optimized Open Graph description"},
        },
    },
}


def get_tool_schemas() -> list[dict]:
    """Return tool schemas in a format suitable for the AI planner prompt."""
    schemas = []
    for name, tool in TOOL_REGISTRY.items():
        schemas.append({
            "name": name,
            "description": tool["description"],
            "parameters": {
                k: {pk: pv for pk, pv in v.items()}
                for k, v in tool["params"].items()
            },
        })
    return schemas


def execute_tool(tool_name: str, params: dict) -> dict:
    """Execute a registered tool and return the result."""
    if tool_name not in TOOL_REGISTRY:
        raise ValueError(f"Unknown tool: {tool_name}")

    tool = TOOL_REGISTRY[tool_name]
    try:
        result = tool["fn"](**params)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Tool {tool_name} failed: {e}")
        return {"success": False, "error": str(e)}
