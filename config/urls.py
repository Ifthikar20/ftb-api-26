from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    path("admin/", admin.site.urls),

    # Health checks
    path("health/", include("health_check.urls")),

    # API v1
    path("api/v1/auth/", include("apps.accounts.api.v1.urls")),
    path("api/v1/websites/", include("apps.websites.api.v1.urls")),
    path("api/v1/analytics/", include("apps.analytics.api.v1.urls")),
    path("api/v1/leads/", include("apps.leads.api.v1.urls")),
    path("api/v1/competitors/", include("apps.competitors.api.v1.urls")),
    path("api/v1/audits/", include("apps.audits.api.v1.urls")),
    path("api/v1/strategy/", include("apps.strategy.api.v1.urls")),
    path("api/v1/notifications/", include("apps.notifications.api.v1.urls")),
    path("api/v1/billing/", include("apps.billing.api.v1.urls")),

    # Pixel ingestion (high throughput)
    path("api/v1/track/", include("apps.analytics.api.v1.pixel_urls")),

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
