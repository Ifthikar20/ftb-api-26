from .base import *  # noqa
import os

DEBUG = False
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
ADMINS = [("Ops Team", env("OPS_EMAIL", default="ops@fetchbot.ai"))]  # noqa: F405
SERVER_EMAIL = env("SERVER_EMAIL", default="noreply@fetchbot.ai")  # noqa: F405

# ── Email Backend (SMTP — works with SES, SendGrid, Mailgun, etc.) ──
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="")  # noqa: F405
EMAIL_PORT = env.int("EMAIL_PORT", default=587)  # noqa: F405
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")  # noqa: F405
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")  # noqa: F405
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)  # noqa: F405
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="FetchBot <noreply@fetchbot.ai>")  # noqa: F405

# If no EMAIL_HOST configured, fall back to console to avoid errors
if not EMAIL_HOST:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ── Trusted Origins (Cloudflare → Nginx → Django) ──
CSRF_TRUSTED_ORIGINS = [
    "https://fetchbot.ai",
    "https://www.fetchbot.ai",
]

# DB SSL — configurable: use "require" for managed DBs (RDS), "prefer" for Docker internal
DB_SSLMODE = env("DB_SSLMODE", default="prefer")  # noqa: F405
DATABASES["default"]["OPTIONS"] = {  # noqa: F405
    "sslmode": DB_SSLMODE,
    "connect_timeout": 10,
}

# AWS S3 Storage
DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
STATICFILES_STORAGE = "storages.backends.s3boto3.S3StaticStorage"
AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", default="")  # noqa: F405
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", default="")  # noqa: F405
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default="")  # noqa: F405
AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="us-east-1")  # noqa: F405
AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com"
AWS_DEFAULT_ACL = "private"
AWS_S3_FILE_OVERWRITE = False

LOG_DIR = os.environ.get("LOG_DIR", "/app/logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOGGING["handlers"].update(  # noqa: F405
    {
        "audit_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": f"{LOG_DIR}/audit.log",
            "maxBytes": 50_000_000,
            "backupCount": 90,
            "formatter": "json",
        },
        "security_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": f"{LOG_DIR}/security.log",
            "maxBytes": 50_000_000,
            "backupCount": 365,
            "formatter": "json",
        },
    }
)
LOGGING["loggers"]["audit"]["handlers"] = ["console", "audit_file"]  # noqa: F405
LOGGING["loggers"]["security"]["handlers"] = ["console", "security_file"]  # noqa: F405

if SENTRY_DSN:  # noqa: F405
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,  # noqa: F405
        integrations=[DjangoIntegration(), CeleryIntegration()],
        traces_sample_rate=0.05,
        environment="production",
    )
