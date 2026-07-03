import dataclasses

from django.apps import AppConfig


class SearchConsoleConfig(AppConfig):
    name = "apps.search_console"
    verbose_name = "Search Console"

    def ready(self):
        """Attach the GSC token-refresh function to the registry config.

        IntegrationConfig is a frozen dataclass, so the callable is bound
        by re-registering a replaced copy. register() keys by config.name,
        so this overwrites the credential-only entry cleanly, and the
        refresh_expiring_tokens beat task picks it up on its next run.
        """
        from apps.search_console.services.oauth_service import refresh_access_token
        from core.integrations import get_registry

        registry = get_registry()
        cfg = registry.get("gsc")
        if cfg is not None and cfg.refresh_token_fn is None:
            registry.register(dataclasses.replace(cfg, refresh_token_fn=refresh_access_token))
