from .base import *  # noqa

DEBUG = True
SECURE_SSL_REDIRECT = False
ALLOWED_HOSTS = ["*"]
CORS_ALLOW_ALL_ORIGINS = True

# Disable rate limiting in dev
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []  # noqa: F405

# Use console email backend
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Disable SSL requirement for DB in dev
DATABASES["default"]["OPTIONS"] = {"connect_timeout": 10}  # noqa: F405

# Don't keep DB connections open in dev. runserver auto-reload leaves the
# prior process's persistent connections idle until CONN_MAX_AGE expires,
# which quickly exhausts Postgres max_connections (default 100).
DATABASES["default"]["CONN_MAX_AGE"] = 0  # noqa: F405
DATABASES["default"]["CONN_HEALTH_CHECKS"] = False  # noqa: F405

# Django Debug Toolbar
try:
    import debug_toolbar  # noqa: F401
    INSTALLED_APPS += ["debug_toolbar"]  # noqa: F405
    MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]  # noqa: F405
    INTERNAL_IPS = ["127.0.0.1"]
except ImportError:
    pass

# Simpler logging in dev — quiet the per-request noise from django.server,
# django_structlog (request_started / request_finished), and the audit
# middleware's INFO-level GET log so the console is readable. Errors,
# warnings, and our own apps logger still surface.
LOGGING["loggers"]["django"]["level"] = "WARNING"  # noqa: F405
LOGGING["loggers"]["django.server"] = {"handlers": ["console"], "level": "WARNING"}  # noqa: F405
LOGGING["loggers"]["django_structlog"] = {"handlers": ["console"], "level": "WARNING"}  # noqa: F405
LOGGING["loggers"]["audit"]["level"] = "WARNING"  # noqa: F405

# Run Celery tasks synchronously in dev (no Redis/worker needed)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
