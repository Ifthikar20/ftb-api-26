from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from apps.analytics.api.v1.tracking_views import TrackedLinkRedirectView
from core.views.version import VersionView

urlpatterns = [
    path("admin/", admin.site.urls),

    # Health checks
    path("health/", include("health_check.urls")),

    # Build identity (unauthenticated; shown in the login page footer)
    path("api/v1/version/", VersionView.as_view(), name="api-version"),

    # API v1
    path("api/v1/auth/", include("apps.accounts.api.v1.urls")),
    path("api/v1/websites/", include("apps.websites.api.v1.urls")),
    path("api/v1/analytics/", include("apps.analytics.api.v1.urls")),
    path("api/v1/notifications/", include("apps.notifications.api.v1.urls")),
    path("api/v1/billing/", include("apps.billing.api.v1.urls")),
    path("api/v1/llm-ranking/", include("apps.llm_ranking.api.v1.urls")),
    path("api/v1/rag/", include("apps.rag.api.v1.urls")),
    path("api/v1/onboarding/", include("apps.onboarding.api.v1.urls")),
    path("api/v1/prompt-library/", include("apps.prompt_library.api.v1.urls")),
    path("api/v1/citations/", include("apps.citations.api.v1.urls")),
    path("api/v1/brand-vault/", include("apps.brand_vault.api.v1.urls")),
    path("api/v1/content-studio/", include("apps.content_studio.api.v1.urls")),
    path("api/v1/agents/", include("apps.agents.api.v1.urls")),
    path("api/v1/search-console/", include("apps.search_console.api.v1.urls")),

    # Pixel ingestion (high throughput)
    path("api/v1/track/", include("apps.analytics.api.v1.pixel_urls")),

    # Tracked link redirect (short URLs — no /api/ prefix intentional)
    path("t/<str:tracking_key>/", TrackedLinkRedirectView.as_view(), name="tracked-link-redirect"),

    # OpenAPI schema
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/schema/swagger/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/schema/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

# Add debug toolbar URLs in dev
if settings.DEBUG:
    try:
        import debug_toolbar  # noqa: F401
        urlpatterns += [path("__debug__/", include("debug_toolbar.urls"))]
    except ImportError:
        pass
