"""
Plan definitions — 2-tier model (Individual + Enterprise).

This is the single source of truth for plan metadata exposed via the API.
For feature-level gating, use constants.PLAN_LIMITS instead.
"""

PLANS = [
    {
        "id": "individual",
        "name": "Individual",
        "segment": "individual",
        "price_monthly": 14,
        "price_yearly": 140,
        "popular": True,
        "features": [
            "3 projects",
            "Up to 50,000 pageviews/month",
            "100 AI credits/month",
            "Lead scoring & hot alerts",
            "5 competitor tracking",
            "SEO audits on-demand",
            "AI strategy & morning briefs",
            "Pipeline builder",
            "Trend intelligence",
            "2 integrations (Slack/Discord/Telegram)",
            "Email support",
        ],
        "limits": {
            "projects": 3,
            "pageviews": 50_000,
            "competitors": 5,
            "team_members": 1,
            "ai_credits": 100,
            "integrations": 2,
        },
    },
    {
        "id": "enterprise",
        "name": "Enterprise",
        "segment": "enterprise",
        "price_monthly": -1,  # Custom
        "price_yearly": -1,
        "features": [
            "Everything in Individual",
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
    "starter": "individual",
    "growth": "individual",
    "free": "individual",
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
