from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class OAuthConfig:
    """OAuth credential settings keys for an integration."""
    client_id_setting: str
    client_secret_setting: str
    scopes: list[str] = field(default_factory=list)
    token_url: str = ""
    authorize_url: str = ""
    token_expiry_seconds: Optional[int] = None


@dataclass(frozen=True)
class ApiKeyConfig:
    """API-key credential settings keys for an integration."""
    api_key_setting: str
    api_secret_setting: str = ""


@dataclass(frozen=True)
class RateLimitConfig:
    """Rate limit constraints for an integration's external API."""
    requests_per_second: float = 10.0
    daily_quota: Optional[int] = None
    celery_rate_limit: str = ""  # e.g. "10/m"


@dataclass(frozen=True)
class TierEntitlement:
    """What a plan tier gets for a specific integration."""
    enabled: bool = False
    feature_key: str = ""  # Key used in PLAN_FEATURES
    limits: dict = field(default_factory=dict)  # e.g. {"webhook_endpoints": 3}


@dataclass(frozen=True)
class IntegrationConfig:
    """Complete configuration for a single integration.

    This is the single source of truth for everything about an integration:
    credentials, entitlements, rate limits, and capabilities.
    """
    name: str               # e.g. "hubspot"
    display_name: str        # e.g. "HubSpot CRM"
    auth_type: str           # "oauth2", "api_key", "webhook_url"

    # Credentials — exactly one of these should be set based on auth_type
    oauth: Optional[OAuthConfig] = None
    api_key: Optional[ApiKeyConfig] = None

    # Per-tier entitlements
    starter: TierEntitlement = field(default_factory=TierEntitlement)
    growth: TierEntitlement = field(default_factory=TierEntitlement)
    scale: TierEntitlement = field(default_factory=TierEntitlement)

    # Rate limits for external API calls
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)

    # Celery queue name for this integration's tasks
    celery_queue: str = "integrations"

    # Webhook event types this integration can emit
    webhook_events: list[str] = field(default_factory=list)

    def tier_entitlement(self, plan: str) -> TierEntitlement:
        """Get entitlement for a plan tier."""
        return getattr(self, plan, TierEntitlement())

    def is_enabled_for(self, plan: str) -> bool:
        """Check if this integration is enabled for a plan."""
        return self.tier_entitlement(plan).enabled

    def feature_key_for(self, plan: str) -> str:
        """Get the PLAN_FEATURES key for this integration at a given tier."""
        return self.tier_entitlement(plan).feature_key

    def get_limit(self, plan: str, limit_name: str, default=None):
        """Get a specific limit for a plan tier."""
        return self.tier_entitlement(plan).limits.get(limit_name, default)

    def get_credentials(self):
        """Load credential values from Django settings.

        Returns a dict with the resolved values (not the setting names).
        """
        from django.conf import settings as django_settings

        if self.auth_type == "oauth2" and self.oauth:
            return {
                "client_id": getattr(django_settings, self.oauth.client_id_setting, ""),
                "client_secret": getattr(django_settings, self.oauth.client_secret_setting, ""),
                "scopes": self.oauth.scopes,
                "token_url": self.oauth.token_url,
                "authorize_url": self.oauth.authorize_url,
            }
        elif self.auth_type == "api_key" and self.api_key:
            result = {
                "api_key": getattr(django_settings, self.api_key.api_key_setting, ""),
            }
            if self.api_key.api_secret_setting:
                result["api_secret"] = getattr(
                    django_settings, self.api_key.api_secret_setting, ""
                )
            return result
        return {}

    def is_configured(self) -> bool:
        """Check if the required credentials are set in Django settings."""
        creds = self.get_credentials()
        if self.auth_type == "oauth2":
            return bool(creds.get("client_id") and creds.get("client_secret"))
        elif self.auth_type == "api_key":
            return bool(creds.get("api_key"))
        elif self.auth_type == "webhook_url":
            return True  # No server-side credentials needed
        return False
