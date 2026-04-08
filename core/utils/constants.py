from django.db import models


class Segment(models.TextChoices):
    INDIVIDUAL = "individual", "Individual"
    ENTERPRISE = "enterprise", "Enterprise"


class Plan(models.TextChoices):
    INDIVIDUAL = "individual", "Individual"
    ENTERPRISE = "enterprise", "Enterprise"
    # Legacy aliases for migration compatibility
    STARTER = "starter", "Starter (Legacy)"
    GROWTH = "growth", "Growth (Legacy)"
    SCALE = "scale", "Scale (Legacy)"


# ── Feature limits per plan ──────────────────────────────────────────
# Individual = $14/mo flat.  Enterprise = custom pricing per user.
PLAN_LIMITS = {
    Plan.INDIVIDUAL: {
        "segment": Segment.INDIVIDUAL,
        "price_monthly": 14,
        "price_yearly": 140,
        "projects": 3,
        "pageviews": 50_000,
        "team_members": 1,
        "ai_credits_monthly": 100,
        "integrations": 2,
        "competitors": 5,
        "pipeline_builder": True,
        "trend_intelligence": True,
        "sso": False,
        "api_access": False,
        "white_label": False,
        "dedicated_support": False,
        # Visible tabs
        "tabs": [
            "dashboard", "projects", "analytics", "leads",
            "heatmaps", "keywords",
            "campaigns", "integrations", "billing", "settings",
        ],
    },
    Plan.ENTERPRISE: {
        "segment": Segment.ENTERPRISE,
        "price_monthly": -1,  # custom
        "price_yearly": -1,
        "projects": -1,
        "pageviews": -1,
        "team_members": -1,  # based on contract
        "ai_credits_monthly": -1,  # unlimited
        "integrations": -1,
        "competitors": -1,
        "pipeline_builder": True,
        "trend_intelligence": True,
        "sso": True,
        "api_access": True,
        "white_label": True,
        "dedicated_support": True,
        # All tabs visible
        "tabs": [
            "dashboard", "projects", "analytics", "leads",
            "heatmaps", "keywords",
            "agents", "campaigns", "llm_ranking",
            "integrations", "billing", "settings",
        ],
    },
}

# Legacy aliases → map to Individual
PLAN_LIMITS[Plan.STARTER] = PLAN_LIMITS[Plan.INDIVIDUAL]
PLAN_LIMITS[Plan.GROWTH] = PLAN_LIMITS[Plan.INDIVIDUAL]
PLAN_LIMITS[Plan.SCALE] = PLAN_LIMITS[Plan.ENTERPRISE]


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
