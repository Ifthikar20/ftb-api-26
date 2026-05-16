"""
Temporary script to create a test user in the database and print credentials.
DELETE THIS FILE after use.

Usage:
    python scripts/create_test_user.py [email] [full_name]

If email/full_name are omitted, randomized values are generated.
"""
import os
import secrets
import string
import sys

import django


def _setup_django():
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
    django.setup()


def _generate_password(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def main() -> int:
    _setup_django()

    from django.contrib.auth import get_user_model

    User = get_user_model()

    email = sys.argv[1] if len(sys.argv) > 1 else f"testuser_{secrets.token_hex(4)}@example.com"
    full_name = sys.argv[2] if len(sys.argv) > 2 else "Test User"
    password = _generate_password()

    if User.objects.filter(email=email).exists():
        print(f"ERROR: user with email {email} already exists.", file=sys.stderr)
        return 1

    user = User.objects.create_user(
        email=email,
        password=password,
        full_name=full_name,
        is_email_verified=True,
    )

    print("Test user created successfully.")
    print("-" * 48)
    print(f"ID:       {user.id}")
    print(f"Email:    {user.email}")
    print(f"Password: {password}")
    print(f"Name:     {user.full_name}")
    print("-" * 48)
    print("Remember to delete this script after use.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
