from django.db import models


class Segment(models.TextChoices):
    INDIVIDUAL = "individual", "Individual"
    ENTERPRISE = "enterprise", "Enterprise"


class Plan(models.TextChoices):
    INDIVIDUAL = "individual", "Individual ($45/mo)"
    PRO = "pro", "Pro ($100/mo)"
    ENTERPRISE = "enterprise", "Business / Enterprise"
    # Legacy aliases for migration compatibility — these still appear
    # on existing Subscription rows and must keep resolving to a real
    # plan via PLAN_LIMITS until a backfill migrates them.
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
    Plan.INDIVIDUAL: {
        "segment": Segment.INDIVIDUAL,
        "price_monthly": 45,
        "price_yearly": 450,
        "trial_days": 0,
        "projects": 1,
        "pageviews": 50_000,
        "team_members": 1,
        "ai_credits_monthly": 150,
        "integrations": 3,
        "max_agents": 1,
        "competitors": 8,
        "max_prompts_per_audit": 5,
        "max_audits_per_month": 4,            # weekly cadence cap
        "providers_allowed": ["claude", "gpt4"],
        "pipeline_builder": True,
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
    Plan.PRO: {
        "segment": Segment.INDIVIDUAL,
        "price_monthly": 100,
        "price_yearly": 1000,
        "trial_days": 0,
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
    Plan.ENTERPRISE: {
        "segment": Segment.ENTERPRISE,
        "price_monthly": -1,  # custom
        "price_yearly": -1,
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

# Legacy aliases — keep resolving so existing Subscription rows don't
# 500 on read. Starter maps to Individual (closest match in the new
# 3-tier model); Growth/Scale follow Starter/Enterprise as before.
PLAN_LIMITS[Plan.STARTER] = PLAN_LIMITS[Plan.INDIVIDUAL]
PLAN_LIMITS[Plan.GROWTH] = PLAN_LIMITS[Plan.INDIVIDUAL]
PLAN_LIMITS[Plan.SCALE] = PLAN_LIMITS[Plan.ENTERPRISE]


def max_prompts_for_user(user) -> int:
    """
    Return the prompts-per-audit cap for ``user``'s current plan.

    Falls back to the Individual cap when the user has no subscription
    or the subscription's plan isn't recognised. Never returns 0 — even
    a user with no subscription can run a tiny 5-prompt audit so the
    "first run" experience isn't gated.
    """
    from django.conf import settings

    if not settings.PAYWALL_ENABLED:
        limits = PLAN_LIMITS[Plan.ENTERPRISE]
    else:
        try:
            sub = getattr(user, "subscription", None)
            plan = getattr(sub, "plan", None) if sub else None
        except Exception:
            plan = None
        limits = PLAN_LIMITS.get(plan) or PLAN_LIMITS[Plan.INDIVIDUAL]
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
