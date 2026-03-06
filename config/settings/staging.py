from .base import *  # noqa

DEBUG = False
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Staging-specific logging with file handlers
import os

LOG_DIR = "/var/log/growthpilot"
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
        traces_sample_rate=0.1,
        environment="staging",
    )
