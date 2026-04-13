"""
Plan definitions — 2-tier model (Starter + Enterprise).

This is the single source of truth for plan metadata exposed via the API.
For feature-level gating, use constants.PLAN_LIMITS instead.
"""

PLANS = [
    {
        "id": "starter",
        "name": "Starter",
        "segment": "individual",
        "price_monthly": 39,
        "price_yearly": 390,
        "trial_days": 5,
        "popular": True,
        "features": [
            "5 projects",
            "Up to 100,000 pageviews/month",
            "200 AI credits/month",
            "Lead scoring & hot alerts",
            "10 competitor tracking",
            "Heatmaps & funnels",
            "Keyword tracking & SEO tools",
            "Pipeline builder",
            "Trend intelligence",
            "3 integrations (Slack/Discord/Telegram)",
            "Email support",
        ],
        "limits": {
            "projects": 5,
            "pageviews": 100_000,
            "competitors": 10,
            "team_members": 1,
            "ai_credits": 200,
            "integrations": 3,
        },
    },
    {
        "id": "enterprise",
        "name": "Enterprise",
        "segment": "enterprise",
        "price_monthly": -1,  # Custom
        "price_yearly": -1,
        "features": [
            "Everything in Starter",
            "Unlimited projects & pageviews",
            "Unlimited AI credits",
            "Unlimited team members",
            "Unlimited competitor tracking",
            "Unlimited integrations",
            "SSO / SAML authentication",
            "Full API access",
            "White-label reports",
            "Agents & LLM Ranking",
            "Organization-level billing",
            "Dedicated support & SLA",
            "Custom onboarding",
        ],
        "limits": {
            "projects": -1,
            "pageviews": -1,
            "competitors": -1,
            "team_members": -1,
            "ai_credits": -1,
            "integrations": -1,
        },
    },
]

# Legacy plan name → 2-tier mapping
_LEGACY_MAP = {
    "individual": "starter",
    "growth": "starter",
    "free": "starter",
    "scale": "enterprise",
    "team": "enterprise",
    "business": "enterprise",
}


class PlanService:
    @staticmethod
    def get_all_plans() -> list:
        return PLANS

    @staticmethod
    def get_plan(plan_id: str) -> dict | None:
        resolved = _LEGACY_MAP.get(plan_id, plan_id)
        return next((p for p in PLANS if p["id"] == resolved), None)

    @staticmethod
    def get_plan_for_segment(segment: str) -> dict | None:
        return next((p for p in PLANS if p["segment"] == segment), None)
