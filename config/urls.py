from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from apps.analytics.api.v1.tracking_views import EmailOpenPixelView, TrackedLinkRedirectView

urlpatterns = [
    path("admin/", admin.site.urls),

    # Health checks
    path("health/", include("health_check.urls")),

    # API v1
    path("api/v1/auth/", include("apps.accounts.api.v1.urls")),
    path("api/v1/websites/", include("apps.websites.api.v1.urls")),
    path("api/v1/analytics/", include("apps.analytics.api.v1.urls")),
    path("api/v1/leads/", include("apps.leads.api.v1.urls")),

    path("api/v1/notifications/", include("apps.notifications.api.v1.urls")),
    path("api/v1/billing/", include("apps.billing.api.v1.urls")),
    path("api/v1/llm-ranking/", include("apps.llm_ranking.api.v1.urls")),
    path("api/v1/social-leads/", include("apps.social_leads.api.v1.urls")),
    path("api/v1/messaging/", include("apps.messaging.api.v1.urls")),

    # Pixel ingestion (high throughput)
    path("api/v1/track/", include("apps.analytics.api.v1.pixel_urls")),

    # Tracked link redirect (short URLs — no /api/ prefix intentional)
    path("t/<str:tracking_key>/", TrackedLinkRedirectView.as_view(), name="tracked-link-redirect"),

    # Email tracking pixel (open tracking)
    path("api/v1/track/open/<uuid:tracking_id>/", EmailOpenPixelView.as_view(), name="email-open-pixel"),

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
