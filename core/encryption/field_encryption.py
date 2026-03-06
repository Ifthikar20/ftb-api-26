from cryptography.fernet import Fernet
from django.conf import settings
from django.db import models


class EncryptedTextField(models.TextField):
    """
    AES-256 encrypted field. Values are encrypted before save
    and decrypted on read. Used for: API keys, webhook URLs,
    OAuth tokens, any PII that must be stored.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _get_fernet(self):
        key = settings.FIELD_ENCRYPTION_KEY
        if not key:
            return None
        return Fernet(key.encode() if isinstance(key, str) else key)

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        fernet = self._get_fernet()
        if not fernet:
            return value
        try:
            return fernet.decrypt(value.encode()).decode()
        except Exception:
            return value

    def get_prep_value(self, value):
        if value is None:
            return value
        fernet = self._get_fernet()
        if not fernet:
            return value
        return fernet.encrypt(value.encode()).decode()

    def to_python(self, value):
        return value
