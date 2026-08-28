from .base import *  # noqa

DEBUG = False

# Same conditional as prod.py: trusting X-Forwarded-Proto on a deployment
# that does not terminate TLS makes request.is_secure() return True over
# http://, which marks every cookie Secure and the browser then discards
# them. Hardcoding it here would defeat the PUBLIC_SCHEME derivation in
# base.py for staging specifically.
if PUBLIC_SCHEME == "https":  # noqa: F405
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
else:
    SECURE_PROXY_SSL_HEADER = None

# Staging-specific logging with file handlers
import os  # noqa: E402

LOG_DIR = "/var/log/cansee"
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
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,  # noqa: F405
        integrations=[DjangoIntegration(), CeleryIntegration()],
        traces_sample_rate=0.1,
        environment="staging",
    )
