import dataclasses

from django.apps import AppConfig


class WebAnalyticsConfig(AppConfig):
    name = "apps.web_analytics"
    verbose_name = "Web Analytics Sources"

    def ready(self):
        """Attach the GA4 token-refresh function to the registry config.

        Mirrors apps/search_console/apps.py: IntegrationConfig is a frozen
        dataclass, so the callable is bound by re-registering a replaced
        copy under the same name ("ga"). The refresh_expiring_tokens beat
        task then keeps connected GA4 tokens fresh with no extra schedule.
        """
        from apps.web_analytics.services.ga4_oauth import refresh_access_token
        from core.integrations import get_registry

        registry = get_registry()
        cfg = registry.get("ga")
        if cfg is not None and cfg.refresh_token_fn is None:
            registry.register(dataclasses.replace(cfg, refresh_token_fn=refresh_access_token))
