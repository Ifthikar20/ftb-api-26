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


def _add_calendar_entry(*, website_id: str, title: str, topic: str = "",
                        content_type: str = "blog", scheduled_date: str = "") -> dict:
    """Add an entry to the content calendar."""
    from apps.strategy.services.calendar_service import CalendarService
    entry = CalendarService.add_entry(
        website_id=website_id, title=title, topic=topic,
        content_type=content_type, scheduled_date=scheduled_date,
    )
    return {"id": str(entry.id), "title": entry.title, "date": str(entry.scheduled_date)}


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
    "add_calendar_entry": {
        "fn": _add_calendar_entry,
        "description": "Add a content entry to the website's content calendar",
        "params": {
            "website_id": {"type": "string", "required": True},
            "title": {"type": "string", "required": True},
            "topic": {"type": "string", "required": False},
            "content_type": {"type": "string", "required": False, "description": "blog, video, social, email"},
            "scheduled_date": {"type": "string", "required": False, "description": "ISO date YYYY-MM-DD"},
        },
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
