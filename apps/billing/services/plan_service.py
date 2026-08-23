"""
Plan metadata exposed via the API — derived from core.utils.constants
so pricing/limits exist in exactly ONE place. (This module previously
carried its own divergent price table; that drift is gone.)

For feature-level gating, use constants.PLAN_LIMITS / plan_limits.py.
"""
from core.utils.constants import PLAN_LIMITS, Plan


def _free() -> dict:
    limits = PLAN_LIMITS[Plan.FREE]
    return {
        "id": "free",
        "name": "Free",
        "segment": str(limits["segment"]),
        "price_monthly": 0,
        "price_yearly": 0,
        "trial_days": 0,
        "features": [
            "$1 of AI usage per month",
            "1 website",
            f"{limits['max_prompts_per_audit']} prompts per audit",
            f"{limits['max_audits_per_month']} audits / month",
            "Claude + GPT-4",
            "Community support",
        ],
        "limits": {
            "projects": limits["projects"],
            "pageviews": limits["pageviews"],
            "competitors": limits["competitors"],
            "team_members": limits["team_members"],
            "ai_credits": limits["ai_credits_monthly"],
            "integrations": limits["integrations"],
        },
    }


def _pro() -> dict:
    limits = PLAN_LIMITS[Plan.PRO]
    return {
        "id": "pro",
        "name": "Pro",
        "segment": str(limits["segment"]),
        "price_monthly": limits["price_monthly"],
        "price_yearly": limits["price_yearly"],
        "trial_days": limits["trial_days"],
        "popular": True,
        "features": [
            f"{limits['projects']} projects",
            f"Up to {limits['pageviews']:,} pageviews/month",
            "Visibility audits across Claude, GPT, Gemini and Perplexity",
            f"{limits['max_prompts_per_audit']} prompts per audit, daily scans",
            f"{limits['max_agents']} hired agents",
            f"{limits['competitors']} competitors tracked",
            f"{limits['team_members']} team members",
            f"{limits['integrations']} integrations (Slack/Discord)",
            "Trend intelligence",
            "API access",
            "Email support",
        ],
        "limits": {
            "projects": limits["projects"],
            "pageviews": limits["pageviews"],
            "competitors": limits["competitors"],
            "team_members": limits["team_members"],
            "ai_credits": limits["ai_credits_monthly"],
            "integrations": limits["integrations"],
        },
    }


def _business() -> dict:
    limits = PLAN_LIMITS[Plan.BUSINESS]
    return {
        "id": "business",
        "name": "Business",
        "segment": str(limits["segment"]),
        "price_monthly": limits["price_monthly"],  # -1 = custom
        "price_yearly": limits["price_yearly"],
        "trial_days": limits["trial_days"],
        "features": [
            "Everything in Pro",
            "Unlimited projects and pageviews",
            "Unlimited AI usage allowance",
            "Unlimited team members",
            "Unlimited competitor tracking",
            "Unlimited integrations",
            "SSO / SAML authentication",
            "White-label reports",
            "Organization-level billing",
            "Dedicated support and SLA",
            "Custom onboarding",
        ],
        "limits": {
            "projects": limits["projects"],
            "pageviews": limits["pageviews"],
            "competitors": limits["competitors"],
            "team_members": limits["team_members"],
            "ai_credits": limits["ai_credits_monthly"],
            "integrations": limits["integrations"],
        },
    }


PLANS = [_free(), _pro(), _business()]

# Legacy plan name → live-tier mapping
_LEGACY_MAP = {
    "individual": "pro",
    "starter": "pro",
    "growth": "pro",
    "scale": "business",
    "team": "business",
    "enterprise": "business",
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
