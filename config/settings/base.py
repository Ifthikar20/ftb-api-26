from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
)

# Read .env file if present
environ.Env.read_env(BASE_DIR / ".env")

# ── CORE ──
SECRET_KEY = env("DJANGO_SECRET_KEY", default="unsafe-secret-key-change-in-production")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

# ── APPS ──
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "django_celery_beat",
    "django_celery_results",
    "channels",
    "drf_spectacular",
    "django_structlog",
    "axes",
    "django_otp",
    "storages",
    "health_check",
    "health_check.db",
    "health_check.cache",
    "health_check.storage",
]

LOCAL_APPS = [
    "apps.accounts",
    "apps.websites",
    "apps.analytics",
    "apps.leads",

    "apps.audits",
    "apps.strategy",
    "apps.notifications",
    "apps.billing",
    "apps.agents",
    "apps.llm_ranking",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ── AUTH ──
AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ── REST FRAMEWORK ──
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "core.interceptors.response_envelope.EnvelopeRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "core.interceptors.throttling.BurstRateThrottle",
        "core.interceptors.throttling.SustainedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "burst": "500/min",
        "sustained": "20000/hour",
        "auth": "60/min",
        "password_reset": "3/hour",
        "ai_generation": "10/hour",
        "pixel_ingest": "10000/min",
    },
    "DEFAULT_PAGINATION_CLASS": "core.interceptors.pagination.StandardPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "EXCEPTION_HANDLER": "core.interceptors.exception_handler.custom_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.URLPathVersioning",
    "DEFAULT_VERSION": "v1",
    "ALLOWED_VERSIONS": ["v1"],
}

# ── JWT CONFIG ──
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=24),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": env("JWT_SIGNING_KEY", default=SECRET_KEY),
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "TOKEN_OBTAIN_SERIALIZER": "apps.accounts.api.v1.serializers.CustomTokenObtainPairSerializer",
}

# ── MIDDLEWARE (ORDER MATTERS) ──
MIDDLEWARE = [
    "core.middleware.request_id.RequestIDMiddleware",
    "core.middleware.security_headers.SecurityHeadersMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "core.middleware.request_sanitizer.RequestSanitizerMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "core.middleware.audit_log.AuditLogMiddleware",
    "core.middleware.rate_limit.AdaptiveRateLimitMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "axes.middleware.AxesMiddleware",
    "core.middleware.correlation.CorrelationMiddleware",
    "django_structlog.middlewares.RequestMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ── DATABASE ──
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME", default="growthpilot"),
        "USER": env("DB_USER", default="postgres"),
        "PASSWORD": env("DB_PASSWORD", default="postgres"),
        "HOST": env("DB_HOST", default="localhost"),
        "PORT": env("DB_PORT", default="5432"),
        "CONN_MAX_AGE": 600,
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {
            "connect_timeout": 10,
        },
    },
}

# ── CACHE ──
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://localhost:6379/0"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
        "KEY_PREFIX": "gp",
        "TIMEOUT": 300,
    }
}

# ── CHANNELS ──
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [env("REDIS_URL", default="redis://localhost:6379/0")],
        },
    },
}

# ── CELERY ──
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/1")
CELERY_RESULT_BACKEND = "django-db"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 300
CELERY_TASK_SOFT_TIME_LIMIT = 240

# ── SECURITY ──
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = "DENY"
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 3600

# ── AXES ──
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(minutes=30)
AXES_LOCKOUT_PARAMETERS = ["ip_address", "username"]
AXES_RESET_ON_SUCCESS = True

# ── CORS ──
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    "accept",
    "authorization",
    "content-type",
    "x-request-id",
    "x-csrftoken",
]

# ── STATIC & MEDIA ──
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ── INTERNATIONALIZATION ──
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── FIELD ENCRYPTION ──
FIELD_ENCRYPTION_KEY = env("FIELD_ENCRYPTION_KEY", default="")

# ── EXTERNAL SERVICES ──
OPENAI_API_KEY = env("OPENAI_API_KEY", default="")
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY", default="")
GOOGLE_SEARCH_API_KEY = env("GOOGLE_SEARCH_API_KEY", default="")
GOOGLE_SEARCH_ENGINE_ID = env("GOOGLE_SEARCH_ENGINE_ID", default="")
STRIPE_SECRET_KEY = env("STRIPE_SECRET_KEY", default="")
STRIPE_WEBHOOK_SECRET = env("STRIPE_WEBHOOK_SECRET", default="")
STRIPE_STARTER_PRICE_ID = env("STRIPE_STARTER_PRICE_ID", default="")
STRIPE_GROWTH_PRICE_ID = env("STRIPE_GROWTH_PRICE_ID", default="")
STRIPE_SCALE_PRICE_ID = env("STRIPE_SCALE_PRICE_ID", default="")
STRIPE_STARTER_ANNUAL_PRICE_ID = env("STRIPE_STARTER_ANNUAL_PRICE_ID", default="")
STRIPE_GROWTH_ANNUAL_PRICE_ID = env("STRIPE_GROWTH_ANNUAL_PRICE_ID", default="")
STRIPE_SCALE_ANNUAL_PRICE_ID = env("STRIPE_SCALE_ANNUAL_PRICE_ID", default="")
SENDGRID_API_KEY = env("SENDGRID_API_KEY", default="")
GOOGLE_OAUTH_CLIENT_ID = env("GOOGLE_OAUTH_CLIENT_ID", default="")
GOOGLE_OAUTH_CLIENT_SECRET = env("GOOGLE_OAUTH_CLIENT_SECRET", default="")
SENTRY_DSN = env("SENTRY_DSN", default="")
DATAFORSEO_LOGIN = env("DATAFORSEO_LOGIN", default="")
DATAFORSEO_PASSWORD = env("DATAFORSEO_PASSWORD", default="")

# ── OpenClaw AI Agent ──
OPENCLAW_GATEWAY_URL = env("OPENCLAW_GATEWAY_URL", default="")
OPENCLAW_AUTH_TOKEN = env("OPENCLAW_AUTH_TOKEN", default="")

# ── INTEGRATION CREDENTIALS ──
# Managed centrally via core.integrations.registry — setting names referenced there.
HUBSPOT_CLIENT_ID = env("HUBSPOT_CLIENT_ID", default="")
HUBSPOT_CLIENT_SECRET = env("HUBSPOT_CLIENT_SECRET", default="")
SEMRUSH_API_KEY = env("SEMRUSH_API_KEY", default="")
SLACK_CLIENT_ID = env("SLACK_CLIENT_ID", default="")
SLACK_CLIENT_SECRET = env("SLACK_CLIENT_SECRET", default="")
MAILCHIMP_API_KEY = env("MAILCHIMP_API_KEY", default="")
CANVA_CLIENT_ID = env("CANVA_CLIENT_ID", default="")
CANVA_CLIENT_SECRET = env("CANVA_CLIENT_SECRET", default="")
GEMINI_API_KEY = env("GEMINI_API_KEY", default="")
PERPLEXITY_API_KEY = env("PERPLEXITY_API_KEY", default="")
DEFAULT_FROM_EMAIL = env("SERVER_EMAIL", default="noreply@growthpilot.io")

# ── LOGGING ──
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "core.logging.formatters.JSONFormatter",
        },
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "WARNING"},
        "apps": {"handlers": ["console"], "level": "INFO"},
        "audit": {"handlers": ["console"], "level": "INFO"},
        "security": {"handlers": ["console"], "level": "INFO"},
    },
}

# ── DRF SPECTACULAR ──
SPECTACULAR_SETTINGS = {
    "TITLE": "GrowthPilot API",
    "DESCRIPTION": "AI-powered growth intelligence platform API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}
