from cryptography.fernet import Fernet


def generate_encryption_key() -> str:
    """Generate a new Fernet encryption key."""
    return Fernet.generate_key().decode()


def rotate_key(old_key: str, new_key: str, encrypted_value: str) -> str:
    """Re-encrypt a value with a new key."""
    old_fernet = Fernet(old_key.encode())
    new_fernet = Fernet(new_key.encode())
    plaintext = old_fernet.decrypt(encrypted_value.encode())
    return new_fernet.encrypt(plaintext).decode()
