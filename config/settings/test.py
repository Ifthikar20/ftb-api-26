from .base import *  # noqa

DEBUG = False
SECURE_SSL_REDIRECT = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "growthpilot_test",
        "USER": "postgres",
        "PASSWORD": "postgres",
        "HOST": "localhost",
        "PORT": "5432",
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# Disable Celery tasks in tests - run synchronously
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Disable throttling in tests
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []  # noqa: F405

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

FIELD_ENCRYPTION_KEY = "YJGq9tGE_J3DT8L-Gg9KBgBBqChfPg1UYGU1cWTc_zI="

# The suite must never escalate findings to the Anthropic judge, even when
# the developer's shell exports a real ANTHROPIC_API_KEY. Tests that cover
# the escalation path re-enable this and mock the client.
BRAND_SECURITY_JUDGE_ENABLED = False

# Alignment scoring must never run eagerly inside unrelated suites
# (CELERY_TASK_ALWAYS_EAGER makes every .delay inline, so each created
# LLMRankingResult would trigger a scoring pass). Tests covering it
# re-enable the flag and inject fake vectors.
CLAIM_VERIFICATION_ENABLED = False

# Force in-process mode for the internal-service facades so exported
# shell variables can never flip the suite into HTTP mode.
INTELLIGENCE_SERVICE_URL = ""
SOURCES_SERVICE_URL = ""
