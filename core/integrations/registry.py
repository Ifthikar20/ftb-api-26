import logging

from .config import (
    ApiKeyConfig,
    IntegrationConfig,
    OAuthConfig,
    RateLimitConfig,
    TierEntitlement,
)

logger = logging.getLogger("apps")

# ──────────────────────────────────────────────
# Integration Definitions — single source of truth
# ──────────────────────────────────────────────

HUBSPOT = IntegrationConfig(
    name="hubspot",
    display_name="HubSpot CRM",
    auth_type="oauth2",
    oauth=OAuthConfig(
        client_id_setting="HUBSPOT_CLIENT_ID",
        client_secret_setting="HUBSPOT_CLIENT_SECRET",
        scopes=["crm.objects.contacts.write", "crm.objects.contacts.read"],
        token_url="https://api.hubapi.com/oauth/v1/token",
        authorize_url="https://app.hubspot.com/oauth/authorize",
        token_expiry_seconds=21600,  # 6 hours
    ),
    starter=TierEntitlement(enabled=False),
    growth=TierEntitlement(
        enabled=True,
        feature_key="hubspot_basic",
        limits={"sync_direction": "outbound"},
    ),
    scale=TierEntitlement(
        enabled=True,
        feature_key="hubspot_advanced",
        limits={"sync_direction": "bidirectional", "timeline_events": True,
                "segment_sync": True, "custom_field_mapping": True},
    ),
    rate_limit=RateLimitConfig(
        requests_per_second=10.0,
        celery_rate_limit="10/m",
    ),
    celery_queue="integrations",
    webhook_events=["lead.scored", "lead.status_changed", "lead.created"],
)

GOOGLE_ADS = IntegrationConfig(
    name="google_ads",
    display_name="Google Ads",
    auth_type="oauth2",
    oauth=OAuthConfig(
        client_id_setting="GOOGLE_OAUTH_CLIENT_ID",
        client_secret_setting="GOOGLE_OAUTH_CLIENT_SECRET",
        scopes=["https://www.googleapis.com/auth/adwords.readonly"],
        token_url="https://oauth2.googleapis.com/token",
        authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
    ),
    starter=TierEntitlement(enabled=False),
    growth=TierEntitlement(
        enabled=True,
        feature_key="google_ads",
        limits={"campaign_level_only": True},
    ),
    scale=TierEntitlement(
        enabled=True,
        feature_key="google_ads_advanced",
        limits={"per_lead_attribution": True, "ai_budget_recs": True,
                "auction_insights": True},
    ),
    rate_limit=RateLimitConfig(
        daily_quota=15000,
        celery_rate_limit="1/m",
    ),
    celery_queue="integrations",
)

SEMRUSH = IntegrationConfig(
    name="semrush",
    display_name="Semrush",
    auth_type="api_key",
    api_key=ApiKeyConfig(
        api_key_setting="SEMRUSH_API_KEY",
    ),
    starter=TierEntitlement(enabled=False),
    growth=TierEntitlement(
        enabled=True,
        feature_key="competitor_intelligence",
        limits={"competitors": 10, "refresh_frequency": "weekly"},
    ),
    scale=TierEntitlement(
        enabled=True,
        feature_key="competitor_intelligence_advanced",
        limits={"competitors": 50, "refresh_frequency": "daily",
                "on_demand_refresh": True},
    ),
    rate_limit=RateLimitConfig(
        requests_per_second=8.0,
        celery_rate_limit="8/s",
    ),
    celery_queue="integrations",
)

SLACK = IntegrationConfig(
    name="slack",
    display_name="Slack",
    auth_type="oauth2",
    oauth=OAuthConfig(
        client_id_setting="SLACK_CLIENT_ID",
        client_secret_setting="SLACK_CLIENT_SECRET",
        scopes=["chat:write", "commands", "incoming-webhook"],
        token_url="https://slack.com/api/oauth.v2.access",
        authorize_url="https://slack.com/oauth/v2/authorize",
    ),
    starter=TierEntitlement(
        enabled=True,
        feature_key="slack_webhook",
        limits={"webhook_only": True},
    ),
    growth=TierEntitlement(
        enabled=True,
        feature_key="slack_app",
        limits={"interactive_buttons": True, "morning_brief": True},
    ),
    scale=TierEntitlement(
        enabled=True,
        feature_key="slack_advanced",
        limits={"slash_commands": True, "team_channels": True,
                "custom_routing": True},
    ),
    rate_limit=RateLimitConfig(
        requests_per_second=1.0,  # 1 msg/sec/channel
        celery_rate_limit="60/m",
    ),
    celery_queue="integrations",
    webhook_events=["lead.scored", "lead.status_changed",
                    "competitor.change_detected", "audit.completed"],
)

WEBHOOKS = IntegrationConfig(
    name="webhooks",
    display_name="Outbound Webhooks",
    auth_type="webhook_url",
    starter=TierEntitlement(enabled=False),
    growth=TierEntitlement(
        enabled=True,
        feature_key="webhooks_basic",
        limits={"max_endpoints": 3, "events": ["lead.scored",
                "lead.status_changed", "lead.created"]},
    ),
    scale=TierEntitlement(
        enabled=True,
        feature_key="webhooks_advanced",
        limits={"max_endpoints": None, "events": "__all__",
                "delivery_logs": True, "custom_headers": True},
    ),
    rate_limit=RateLimitConfig(
        requests_per_second=100.0,
        celery_rate_limit="100/m",
    ),
    celery_queue="webhooks",
    webhook_events=[
        "lead.scored", "lead.status_changed", "lead.created",
        "competitor.change_detected", "audit.completed", "visitor.identified",
    ],
)

GOOGLE_ANALYTICS = IntegrationConfig(
    name="ga",
    display_name="Google Analytics",
    auth_type="oauth2",
    oauth=OAuthConfig(
        client_id_setting="GOOGLE_OAUTH_CLIENT_ID",
        client_secret_setting="GOOGLE_OAUTH_CLIENT_SECRET",
        scopes=["https://www.googleapis.com/auth/analytics.readonly"],
        token_url="https://oauth2.googleapis.com/token",
        authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
    ),
    starter=TierEntitlement(enabled=True, feature_key="basic_analytics"),
    growth=TierEntitlement(enabled=True, feature_key="full_analytics"),
    scale=TierEntitlement(enabled=True, feature_key="full_analytics"),
)

GOOGLE_SEARCH_CONSOLE = IntegrationConfig(
    name="gsc",
    display_name="Google Search Console",
    auth_type="oauth2",
    oauth=OAuthConfig(
        client_id_setting="GOOGLE_OAUTH_CLIENT_ID",
        client_secret_setting="GOOGLE_OAUTH_CLIENT_SECRET",
        scopes=["https://www.googleapis.com/auth/webmasters.readonly"],
        token_url="https://oauth2.googleapis.com/token",
        authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
    ),
    starter=TierEntitlement(enabled=True, feature_key="basic_analytics"),
    growth=TierEntitlement(enabled=True, feature_key="full_analytics"),
    scale=TierEntitlement(enabled=True, feature_key="full_analytics"),
)

MAILCHIMP = IntegrationConfig(
    name="mailchimp",
    display_name="Mailchimp",
    auth_type="api_key",
    api_key=ApiKeyConfig(
        api_key_setting="MAILCHIMP_API_KEY",
    ),
    starter=TierEntitlement(enabled=False),
    growth=TierEntitlement(
        enabled=True,
        feature_key="mailchimp",
        limits={"max_contacts": 5000, "campaigns_per_month": 10},
    ),
    scale=TierEntitlement(
        enabled=True,
        feature_key="mailchimp_advanced",
        limits={"max_contacts": None, "campaigns_per_month": None, "automation": True},
    ),
    rate_limit=RateLimitConfig(
        requests_per_second=10.0,
        celery_rate_limit="10/s",
    ),
    celery_queue="integrations",
    webhook_events=["campaign.sent"],
)

GOOGLE_DRIVE = IntegrationConfig(
    name="google_drive",
    display_name="Google Drive",
    auth_type="oauth2",
    oauth=OAuthConfig(
        client_id_setting="GOOGLE_OAUTH_CLIENT_ID",
        client_secret_setting="GOOGLE_OAUTH_CLIENT_SECRET",
        scopes=[
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/spreadsheets",
        ],
        token_url="https://oauth2.googleapis.com/token",
        authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
    ),
    starter=TierEntitlement(enabled=False),
    growth=TierEntitlement(
        enabled=True,
        feature_key="google_drive",
        limits={"export_formats": ["leads", "campaigns"]},
    ),
    scale=TierEntitlement(
        enabled=True,
        feature_key="google_drive_advanced",
        limits={"export_formats": ["leads", "campaigns", "analytics"], "auto_sync": True},
    ),
    rate_limit=RateLimitConfig(
        requests_per_second=5.0,
        celery_rate_limit="5/s",
    ),
    celery_queue="integrations",
)

CANVA = IntegrationConfig(
    name="canva",
    display_name="Canva",
    auth_type="oauth2",
    oauth=OAuthConfig(
        client_id_setting="CANVA_CLIENT_ID",
        client_secret_setting="CANVA_CLIENT_SECRET",
        scopes=["design:content:read", "design:meta:read"],
        token_url="https://api.canva.com/rest/v1/oauth/token",
        authorize_url="https://www.canva.com/api/oauth/authorize",
    ),
    starter=TierEntitlement(enabled=False),
    growth=TierEntitlement(
        enabled=True,
        feature_key="canva",
        limits={"design_links": True},
    ),
    scale=TierEntitlement(
        enabled=True,
        feature_key="canva_advanced",
        limits={"design_links": True, "design_import": True},
    ),
    rate_limit=RateLimitConfig(
        requests_per_second=2.0,
        celery_rate_limit="2/s",
    ),
    celery_queue="integrations",
)


class IntegrationRegistry:
    """Central registry for all integration configurations.

    Usage:
        registry = get_registry()
        config = registry.get("hubspot")
        if config.is_enabled_for(user.plan):
            creds = config.get_credentials()
    """

    def __init__(self):
        self._integrations: dict[str, IntegrationConfig] = {}

    def register(self, config: IntegrationConfig):
        self._integrations[config.name] = config

    def get(self, name: str) -> IntegrationConfig | None:
        return self._integrations.get(name)

    def all(self) -> dict[str, IntegrationConfig]:
        return dict(self._integrations)

    def enabled_for(self, plan: str) -> list[IntegrationConfig]:
        """Return all integrations enabled for a plan tier."""
        return [c for c in self._integrations.values() if c.is_enabled_for(plan)]

    def configured(self) -> list[IntegrationConfig]:
        """Return all integrations that have credentials configured."""
        return [c for c in self._integrations.values() if c.is_configured()]

    def feature_keys_for(self, plan: str) -> list[str]:
        """Return all PLAN_FEATURES keys for a plan tier."""
        keys = []
        for config in self._integrations.values():
            key = config.feature_key_for(plan)
            if key:
                keys.append(key)
        return keys

    def integration_choices(self) -> list[tuple[str, str]]:
        """Return Django model choices for integration types."""
        return [(c.name, c.display_name) for c in self._integrations.values()]

    def check_entitlement(self, user, integration_name: str) -> bool:
        """Check if a user's plan allows an integration."""
        config = self.get(integration_name)
        if not config:
            return False
        plan = getattr(user, "plan", "starter")
        return config.is_enabled_for(plan)

    def get_limit(self, user, integration_name: str, limit_name: str, default=None):
        """Get a specific limit for a user's plan and integration."""
        config = self.get(integration_name)
        if not config:
            return default
        plan = getattr(user, "plan", "starter")
        return config.get_limit(plan, limit_name, default)


# ── Singleton ──

_registry: IntegrationRegistry | None = None


def get_registry() -> IntegrationRegistry:
    """Get the global integration registry (created once)."""
    global _registry
    if _registry is None:
        _registry = IntegrationRegistry()
        for config in [
            HUBSPOT, GOOGLE_ADS, SEMRUSH, SLACK, WEBHOOKS,
            GOOGLE_ANALYTICS, GOOGLE_SEARCH_CONSOLE,
            MAILCHIMP, GOOGLE_DRIVE, CANVA,
        ]:
            _registry.register(config)
    return _registry
