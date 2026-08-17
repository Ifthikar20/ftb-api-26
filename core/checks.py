"""Project-wide Django system checks.

Registered from apps.accounts.apps.AccountsConfig.ready() so they run on every
``manage.py check`` (and therefore in CI and at deploy time).
"""
from django.conf import settings
from django.core.checks import Error, Tags, register


@register(Tags.security)
def check_field_encryption_key(app_configs, **kwargs):
    """Error when field encryption is required but the key is missing/invalid.

    Pairs with core.encryption.field_encryption.EncryptedTextField, which fails
    closed at read/write time; this surfaces the misconfiguration up front via
    ``manage.py check --deploy`` instead of at the first secret read.
    """
    errors = []
    if not getattr(settings, "FIELD_ENCRYPTION_REQUIRED", False):
        return errors

    key = getattr(settings, "FIELD_ENCRYPTION_KEY", "") or ""
    if not key:
        errors.append(
            Error(
                "FIELD_ENCRYPTION_REQUIRED is set but FIELD_ENCRYPTION_KEY is empty.",
                hint=(
                    "Generate one with: python -c "
                    "\"from cryptography.fernet import Fernet; "
                    "print(Fernet.generate_key().decode())\" and set "
                    "FIELD_ENCRYPTION_KEY in the environment."
                ),
                id="core.E001",
            )
        )
        return errors

    try:
        from cryptography.fernet import Fernet

        Fernet(key.encode() if isinstance(key, str) else key)
    except Exception as exc:  # noqa: BLE001 — any parse failure is a config error
        errors.append(
            Error(
                f"FIELD_ENCRYPTION_KEY is not a valid Fernet key: {exc}",
                hint="It must be a url-safe base64-encoded 32-byte key.",
                id="core.E002",
            )
        )
    return errors
