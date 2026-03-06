PLANS = [
    {
        "id": "starter",
        "name": "Starter",
        "price_monthly": 29,
        "price_yearly": 290,
        "features": [
            "1 website",
            "Up to 10,000 pageviews/month",
            "Basic lead tracking",
            "3 competitor tracking",
            "Weekly website audit",
            "Email support",
        ],
        "limits": {
            "websites": 1,
            "pageviews": 10000,
            "competitors": 3,
            "team_members": 1,
        },
    },
    {
        "id": "growth",
        "name": "Growth",
        "price_monthly": 79,
        "price_yearly": 790,
        "popular": True,
        "features": [
            "Up to 5 websites",
            "Unlimited pageviews",
            "AI strategy & chat",
            "10 competitor tracking",
            "Content calendar",
            "5 team members",
            "Priority support",
        ],
        "limits": {
            "websites": 5,
            "pageviews": -1,  # Unlimited
            "competitors": 10,
            "team_members": 5,
        },
    },
    {
        "id": "scale",
        "name": "Scale",
        "price_monthly": 199,
        "price_yearly": 1990,
        "features": [
            "Unlimited websites",
            "Unlimited pageviews",
            "AI strategy & chat",
            "50 competitor tracking",
            "Content calendar",
            "Unlimited team members",
            "API access",
            "White label",
            "Dedicated support",
        ],
        "limits": {
            "websites": -1,
            "pageviews": -1,
            "competitors": 50,
            "team_members": -1,
        },
    },
]


class PlanService:
    @staticmethod
    def get_all_plans() -> list:
        return PLANS

    @staticmethod
    def get_plan(plan_id: str) -> dict:
        return next((p for p in PLANS if p["id"] == plan_id), None)
