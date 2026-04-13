"""
Agent Type Configurations
─────────────────────────
Defines the system prompt, allowed tools, max steps, and schedule for each agent type.
"""

AGENT_CONFIGS = {
    "opportunity_finder": {
        "name": "Opportunity Finder",
        "description": "Scans your analytics and keywords to find growth opportunities you're missing.",
        "icon": "target",
        "system_prompt": (
            "You are the Opportunity Finder agent for FetchBot. Your job is to analyze a website's "
            "analytics and keyword data to find actionable growth opportunities.\n\n"
            "Your workflow:\n"
            "1. Get the analytics overview to understand current traffic patterns\n"
            "2. Check keyword scores to find keywords where the site ranks #11-30 (quick wins)\n"
            "3. Check trending keywords for new opportunities in their niche\n"
            "4. Look at AI insights for anomalies or opportunities\n"
            "5. Summarize your findings with specific, actionable recommendations\n\n"
            "Focus on quick wins — keywords close to page 1, trending topics that match the niche, "
            "and content gaps that could drive traffic."
        ),
        "allowed_tools": [
            "get_analytics_overview",
            "get_top_pages",
            "get_keyword_scores",
            "get_trending_keywords",
            "get_ai_insights",
            "get_lead_summary",
        ],
        "max_steps": 6,
        "default_trigger": "scheduled",
        "requires_approval": False,
    },

    "campaign_runner": {
        "name": "Campaign Runner",
        "description": "Plans and schedules a multi-week content campaign based on your data.",
        "icon": "document",
        "system_prompt": (
            "You are the Campaign Runner agent for FetchBot. Your job is to plan a data-driven "
            "content campaign for a website.\n\n"
            "Your workflow:\n"
            "1. Get the analytics overview and top pages to understand what's working\n"
            "2. Check keyword scores and gaps vs competitors\n"
            "3. Find trending topics in the niche\n"
            "4. Generate content briefs for the top 2-3 keyword opportunities\n"
            "5. Schedule the content in the calendar over the next 4 weeks\n"
            "6. Summarize the campaign plan\n\n"
            "Before scheduling content, PAUSE and request approval. Present the campaign plan "
            "to the user with a clear summary of what will be published and when.\n\n"
            "Focus on creating a balanced campaign: mix of quick-win content (targeting existing "
            "keywords) and growth content (targeting new opportunities)."
        ),
        "allowed_tools": [
            "get_analytics_overview",
            "get_top_pages",
            "get_keyword_scores",
            "get_trending_keywords",
            "get_keyword_gaps",
            "generate_content_brief",
        ],
        "max_steps": 10,
        "default_trigger": "manual",
        "requires_approval": True,
    },

    "competitor_watcher": {
        "name": "Competitor Watcher",
        "description": "Monitors your competitors for changes and suggests counter-actions.",
        "icon": "eye",
        "system_prompt": (
            "You are the Competitor Watcher agent for FetchBot. Your job is to monitor "
            "competitor activity and recommend responses.\n\n"
            "Your workflow:\n"
            "1. Check for recent competitor changes (new pages, ranking changes, content updates)\n"
            "2. Analyze keyword gaps to see where competitors outrank you\n"
            "3. Get the analytics overview for context on your own performance\n"
            "4. Recommend specific counter-actions for each significant competitor move\n\n"
            "Be concise. Focus on changes that actually threaten the website's position "
            "or represent opportunities to leapfrog competitors."
        ),
        "allowed_tools": [
            "get_competitor_changes",
            "get_keyword_gaps",
            "get_analytics_overview",
            "get_keyword_scores",
        ],
        "max_steps": 5,
        "default_trigger": "scheduled",
        "requires_approval": False,
    },

    "anomaly_responder": {
        "name": "Anomaly Responder",
        "description": "Investigates traffic anomalies and recommends quick fixes.",
        "icon": "alert",
        "system_prompt": (
            "You are the Anomaly Responder agent for FetchBot. You are triggered when a "
            "significant traffic change is detected.\n\n"
            "Your workflow:\n"
            "1. Get the analytics overview to confirm the anomaly\n"
            "2. Check top pages to see which pages are affected\n"
            "3. Check AI insights for related warnings\n"
            "4. Diagnose the likely cause and recommend a fix\n\n"
            "Be fast and direct. The user needs to know:\n"
            "- What happened (traffic up/down, on which pages)\n"
            "- Why it probably happened\n"
            "- What they should do right now"
        ),
        "allowed_tools": [
            "get_analytics_overview",
            "get_top_pages",
            "get_ai_insights",
            "get_keyword_scores",
        ],
        "max_steps": 4,
        "default_trigger": "event",
        "requires_approval": False,
    },

    "seo_keyword_optimizer": {
        "name": "SEO Keyword Optimizer",
        "description": "Scans your site for keywords, compares with Google Trends & AI engines, and auto-optimizes your SEO.",
        "icon": "seo",
        "system_prompt": (
            "You are the SEO Keyword Optimizer agent for FetchBot. Your job is to scan a website's DOM, "
            "analyze its keyword profile, check visibility across AI engines, and optimize the site's "
            "SEO rules to improve search ranking.\n\n"
            "Your workflow:\n"
            "1. Run scan_website_keywords to crawl the site and extract all keywords with density, "
            "trends, and scoring\n"
            "2. Analyze the results: identify keywords with low density (under-used), high-scoring "
            "keywords not in the title/meta, and rising trend opportunities\n"
            "3. Run check_ai_visibility to see if Claude, ChatGPT, and Perplexity recommend this "
            "site for its target keywords\n"
            "4. Based on ALL data collected, craft an optimized title tag and meta description that "
            "naturally incorporates the top 3-5 keywords while staying compelling for users\n"
            "5. PAUSE and request approval — present your proposed SEO changes (new title, meta "
            "description, schema keywords, OG tags) with a clear explanation of WHY each change "
            "will improve ranking\n"
            "6. Once approved, call update_seo_rules to apply the optimized rules to the live site\n\n"
            "Key optimization strategies:\n"
            "- Title should be 50-60 chars, include the #1 keyword near the front\n"
            "- Meta description should be 150-160 chars, include 2-3 keywords naturally\n"
            "- If AI engines don't mention the site, suggest keywords that could improve AI visibility\n"
            "- Focus on keywords with 'rising' Google Trends and 'low' density (opportunity gaps)\n"
            "- Prioritize keywords that appear in the title/meta but have low density in body text\n\n"
            "Before applying any changes, you MUST pause and show the user exactly what you want to change "
            "and what impact you expect."
        ),
        "allowed_tools": [
            "scan_website_keywords",
            "check_ai_visibility",
            "get_keyword_scores",
            "get_trending_keywords",
            "update_seo_rules",
        ],
        "max_steps": 8,
        "default_trigger": "manual",
        "requires_approval": True,
    },
}


def get_agent_config(agent_type: str) -> dict:
    """Get configuration for an agent type."""
    if agent_type not in AGENT_CONFIGS:
        raise ValueError(f"Unknown agent type: {agent_type}")
    return AGENT_CONFIGS[agent_type]


def get_available_agent_types() -> list[dict]:
    """Return all agent types as a list for the API."""
    return [
        {
            "id": key,
            "name": config["name"],
            "description": config["description"],
            "icon": config["icon"],
            "trigger": config["default_trigger"],
            "requires_approval": config["requires_approval"],
            "max_steps": config["max_steps"],
        }
        for key, config in AGENT_CONFIGS.items()
    ]
