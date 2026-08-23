from django.db import models


class Segment(models.TextChoices):
    INDIVIDUAL = "individual", "Individual"
    ENTERPRISE = "enterprise", "Enterprise"


class Plan(models.TextChoices):
    # ── Live model (2026-08): Free -> Pro $45/mo self-serve -> Business custom ──
    FREE = "free", "Free"
    PRO = "pro", "Pro ($45/mo)"
    BUSINESS = "business", "Business (custom)"
    # Legacy aliases for migration compatibility — these still appear
    # on existing Subscription/User rows and must keep resolving to a
    # real plan via PLAN_LIMITS until a backfill migrates them.
    INDIVIDUAL = "individual", "Individual (Legacy)"
    ENTERPRISE = "enterprise", "Enterprise (Legacy)"
    STARTER = "starter", "Starter (Legacy)"
    GROWTH = "growth", "Growth (Legacy)"
    SCALE = "scale", "Scale (Legacy)"


# ── Feature limits per plan ──────────────────────────────────────────
#
# ``max_prompts_per_audit`` is the headline LLM-ranking gate — every
# call to ``LLMRankingService.generate_prompts`` reads this off the
# user's current plan and caps the prompt list accordingly. Bumping a
# user's tier widens the cap on the next audit immediately.
PLAN_LIMITS = {
    # Free: what an account WITHOUT an active/trialing subscription gets.
    # The AI allowance is a small acquisition cost (settings.
    # AI_FREE_MONTHLY_CAP_USD, default $1/month) — enough to feel the
    # product, not enough to burn margin.
    Plan.FREE: {
        "segment": Segment.INDIVIDUAL,
        "price_monthly": 0,
        "price_yearly": 0,
        "trial_days": 0,
        "projects": 1,
        "pageviews": 10_000,
        "team_members": 1,
        "ai_credits_monthly": 50,
        "integrations": 1,
        "max_agents": 1,
        "competitors": 3,
        "max_prompts_per_audit": 5,
        "max_audits_per_month": 2,
        "providers_allowed": ["claude", "gpt4"],
        "pipeline_builder": False,
        "trend_intelligence": False,
        "sso": False,
        "api_access": False,
        "white_label": False,
        "dedicated_support": False,
        "tabs": [
            "dashboard", "projects", "analytics", "leads",
            "heatmaps", "keywords",
            "llm_ranking",
            "integrations", "billing", "settings",
        ],
    },
    # Pro carries the full self-serve feature set at $45/mo. The AI spend
    # wall (65% of price -> $29.25/mo of model cost) is what protects
    # margin, so the feature limits can stay generous.
    Plan.PRO: {
        "segment": Segment.INDIVIDUAL,
        "price_monthly": 45,
        "price_yearly": 450,
        "trial_days": 7,
        "projects": 5,
        "pageviews": 250_000,
        "team_members": 5,
        "ai_credits_monthly": 600,
        "integrations": 10,
        "max_agents": 5,
        "competitors": 25,
        "max_prompts_per_audit": 15,
        "max_audits_per_month": 30,           # daily cadence cap
        "providers_allowed": ["claude", "gpt4", "gemini", "perplexity"],
        "pipeline_builder": True,
        "trend_intelligence": True,
        "sso": False,
        "api_access": True,
        "white_label": False,
        "dedicated_support": False,
        "tabs": [
            "dashboard", "projects", "analytics", "leads",
            "heatmaps", "keywords",
            "llm_ranking",
            "integrations", "billing", "settings",
        ],
    },
    Plan.BUSINESS: {
        "segment": Segment.ENTERPRISE,
        "price_monthly": -1,  # custom — contact sales
        "price_yearly": -1,
        "trial_days": 0,
        "projects": -1,
        "pageviews": -1,
        "team_members": -1,
        "ai_credits_monthly": -1,
        "integrations": -1,
        "max_agents": -1,
        "competitors": -1,
        "max_prompts_per_audit": 50,
        "max_audits_per_month": -1,
        "providers_allowed": ["claude", "gpt4", "gemini", "perplexity"],
        "pipeline_builder": True,
        "trend_intelligence": True,
        "sso": True,
        "api_access": True,
        "white_label": True,
        "dedicated_support": True,
        "tabs": [
            "dashboard", "projects", "analytics", "leads",
            "heatmaps", "keywords",
            "llm_ranking",
            "integrations", "billing", "settings",
        ],
    },
}

# Legacy aliases — keep resolving so existing Subscription/User rows
# don't 500 on read. Every historical self-serve tier maps to Pro; the
# historical top tiers map to Business.
PLAN_LIMITS[Plan.INDIVIDUAL] = PLAN_LIMITS[Plan.PRO]
PLAN_LIMITS[Plan.STARTER] = PLAN_LIMITS[Plan.PRO]
PLAN_LIMITS[Plan.GROWTH] = PLAN_LIMITS[Plan.PRO]
PLAN_LIMITS[Plan.ENTERPRISE] = PLAN_LIMITS[Plan.BUSINESS]
PLAN_LIMITS[Plan.SCALE] = PLAN_LIMITS[Plan.BUSINESS]


# The RBAC feature lists and the integrations registry still key their
# tier tables on the historical starter/growth/scale names. This maps
# ANY plan value (live or legacy) onto those table keys so a plan="pro"
# or plan="business" user resolves entitlements correctly.
LEGACY_TIER_KEY = {
    "pro": "growth",
    "business": "scale",
    "individual": "growth",
    "enterprise": "scale",
    "free": "starter",
    "team": "scale",
    "starter": "starter",
    "growth": "growth",
    "scale": "scale",
}


def legacy_tier_key(plan: str) -> str:
    """Map a plan value onto the starter/growth/scale tier-table keys."""
    return LEGACY_TIER_KEY.get(plan, "growth")


def max_prompts_for_user(user) -> int:
    """
    Return the prompts-per-audit cap for ``user``'s current plan.

    Resolves the plan through ``current_plan_for`` (the single source of
    truth): an active/trialing subscription grants its tier, everything
    else — no row, canceled, past due, lapsed trial — is the Free cap.
    Never returns 0: even a Free user can run a tiny 5-prompt audit so
    the "first run" experience isn't gated.
    """
    from django.conf import settings

    if not settings.PAYWALL_ENABLED:
        limits = PLAN_LIMITS[Plan.BUSINESS]
    else:
        from apps.billing.services.plan_limits import current_plan_for

        limits = PLAN_LIMITS.get(current_plan_for(user)) or PLAN_LIMITS[Plan.FREE]
    raw = limits.get("max_prompts_per_audit") or 5
    cap = int(raw) if isinstance(raw, int | float) else 5
    return cap if cap > 0 else 50  # treat -1 as "effectively unlimited"


class UserRole(models.TextChoices):
    OWNER = "owner", "Owner"
    ADMIN = "admin", "Admin"
    EDITOR = "editor", "Editor"
    VIEWER = "viewer", "Viewer"


class AuditStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    RUNNING = "running", "Running"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class IssueSeverity(models.TextChoices):
    CRITICAL = "critical", "Critical"
    WARNING = "warning", "Warning"
    INFO = "info", "Info"


class LeadStatus(models.TextChoices):
    NEW = "new", "New"
    CONTACTED = "contacted", "Contacted"
    QUALIFIED = "qualified", "Qualified"
    CUSTOMER = "customer", "Customer"
    LOST = "lost", "Lost"


class ContentType(models.TextChoices):
    BLOG = "blog", "Blog Post"
    SOCIAL = "social", "Social Media"
    EMAIL = "email", "Email"
    VIDEO = "video", "Video"


class ActionStatus(models.TextChoices):
    TODO = "todo", "To Do"
    IN_PROGRESS = "in_progress", "In Progress"
    DONE = "done", "Done"
    SKIPPED = "skipped", "Skipped"


class ThreatLevel(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    CRITICAL = "critical", "Critical"


class SubscriptionStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    PAST_DUE = "past_due", "Past Due"
    CANCELED = "canceled", "Canceled"
    TRIALING = "trialing", "Trialing"
    INCOMPLETE = "incomplete", "Incomplete"
