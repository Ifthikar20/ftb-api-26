import logging

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models

logger = logging.getLogger("apps")

# Ciphertext written by this field is prefixed with a version marker so a
# value can be classified deterministically as encrypted-vs-plaintext on read
# (previously a decrypt failure silently returned the raw bytes). Bump the
# version if the scheme changes.
_MARKER = "enc$v1$"

# Emit the "running without encryption" warning only once per process rather
# than on every write, so dev logs stay readable.
_warned_no_key = False


class EncryptedTextField(models.TextField):
    """
    AES-256 (Fernet) encrypted field. Values are encrypted before save and
    decrypted on read. Used for OAuth tokens, webhook secrets/URLs, and any
    other secret that must be stored.

    Fail-closed behavior (see also core.checks.check_field_encryption_key):
      * When ``settings.FIELD_ENCRYPTION_REQUIRED`` is true and no key is
        configured, this raises ``ImproperlyConfigured`` rather than silently
        storing plaintext. Prod sets REQUIRED=True.
      * When a stored value is marked as encrypted but cannot be decrypted,
        this raises rather than returning the raw ciphertext.
      * In dev (REQUIRED false, no key) it degrades to plaintext, but loudly:
        a one-time WARNING is logged.
    """

    def _get_fernet(self):
        key = settings.FIELD_ENCRYPTION_KEY
        if not key:
            if getattr(settings, "FIELD_ENCRYPTION_REQUIRED", False):
                raise ImproperlyConfigured(
                    "FIELD_ENCRYPTION_KEY is required (FIELD_ENCRYPTION_REQUIRED "
                    "is set) but is empty. Encrypted fields refuse to read or "
                    "write plaintext in this configuration."
                )
            global _warned_no_key
            if not _warned_no_key:
                logger.warning(
                    "FIELD_ENCRYPTION_KEY is empty and FIELD_ENCRYPTION_REQUIRED "
                    "is not set: EncryptedTextField values are stored as PLAINTEXT. "
                    "Set both before handling real secrets."
                )
                _warned_no_key = True
            return None
        return Fernet(key.encode() if isinstance(key, str) else key)

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        if not value.startswith(_MARKER):
            # No marker: legacy/plaintext value written before encryption was
            # enabled (or a dev row). Return as-is.
            return value
        fernet = self._get_fernet()
        if fernet is None:
            # Marker present but no key available. The data IS encrypted; we
            # must not hand back ciphertext as if it were the plaintext.
            raise ImproperlyConfigured(
                "An encrypted field value was read but FIELD_ENCRYPTION_KEY is "
                "not configured to decrypt it."
            )
        token = value[len(_MARKER):]
        try:
            return fernet.decrypt(token.encode()).decode()
        except InvalidToken as exc:
            # Fail closed: a wrong/rotated key or tampered ciphertext must
            # surface, not silently return the raw bytes to the caller.
            raise ImproperlyConfigured(
                "Failed to decrypt an encrypted field value (wrong key or "
                "corrupted data)."
            ) from exc

    def get_prep_value(self, value):
        if value is None:
            return value
        fernet = self._get_fernet()
        if fernet is None:
            # Dev-only plaintext path (REQUIRED is false); already warned.
            return value
        return _MARKER + fernet.encrypt(str(value).encode()).decode()

    def to_python(self, value):
        return value
