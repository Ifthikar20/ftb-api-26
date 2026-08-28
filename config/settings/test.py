from .base import *  # noqa

DEBUG = False
SECURE_SSL_REDIRECT = False

# The suite asserts the secure posture, so it must not inherit a developer's
# exported PUBLIC_SCHEME=http -- that would silently change what a dozen
# unrelated tests are checking. Tests that need plaintext behaviour use
# override_settings on the derived values instead. Mirrors the pinning of
# POLAR_ACCESS_TOKEN / RAG_VECTOR_BACKEND further down this file.
PUBLIC_SCHEME = "https"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "cansee_test",
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

# Polar metering must never leave the process in tests: no outbox rows
# unless a test opts in via override_settings, never a real token, and
# reads always come from the local ledger. Mirrors the facade pattern
# above so an exported shell POLAR_ACCESS_TOKEN can't flip the suite.
POLAR_ACCESS_TOKEN = ""
POLAR_INGEST_MODE = "off"
POLAR_READS_ENABLED = False

# The suite must stay deterministic and offline: pin retrieval to the
# Python path regardless of what the developer's .env sets. Tests that
# cover the vector backend opt in per-test via override_settings, with
# a tmp-dir index - never the shared dev server.
RAG_VECTOR_BACKEND = "python"
RAG_CHROMA_URL = ""

# Deterministic free-plan allowance regardless of the developer's .env
# (local dev raises it so the $1 default doesn't stall testing).
AI_FREE_MONTHLY_CAP_USD = 1.0
