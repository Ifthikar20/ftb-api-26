"""
Temporary script to create test/dummy users in the database and print credentials.
DELETE THIS FILE after use.

Usage:
    # Create a single user (random email/name if omitted)
    python scripts/create_test_user.py [email] [full_name]

    # Create N dummy users at once
    python scripts/create_test_user.py --count 5
"""
import argparse
import os
import secrets
import string
import sys

import django


def _setup_django():
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
    django.setup()


SIMPLE_PASSWORD = "TestPass1234"


def _generate_password(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


_FIRST_NAMES = [
    "Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Quinn",
    "Avery", "Skyler", "Drew", "Hayden", "Reese", "Parker", "Rowan",
]
_LAST_NAMES = [
    "Smith", "Johnson", "Garcia", "Lee", "Brown", "Davis", "Miller",
    "Wilson", "Anderson", "Thomas", "Martinez", "Clark", "Lewis", "Walker",
]


def _random_full_name() -> str:
    return f"{secrets.choice(_FIRST_NAMES)} {secrets.choice(_LAST_NAMES)}"


def _create_one(User, email: str, full_name: str, password: str) -> tuple[str, str, str] | None:
    if User.objects.filter(email=email).exists():
        print(f"SKIP: {email} already exists.", file=sys.stderr)
        return None
    user = User.objects.create_user(
        email=email,
        password=password,
        full_name=full_name,
        is_email_verified=True,
    )
    return str(user.id), user.email, password


def main() -> int:
    parser = argparse.ArgumentParser(description="Create test/dummy users.")
    parser.add_argument("email", nargs="?", help="Email for a single user.")
    parser.add_argument("full_name", nargs="?", help="Full name for a single user.")
    parser.add_argument(
        "--count", "-n", type=int, default=None,
        help="Create N dummy users with randomized email/name.",
    )
    parser.add_argument(
        "--simple-password", action="store_true",
        help=f"Use a simple shared password ({SIMPLE_PASSWORD!r}) instead of a random one.",
    )
    args = parser.parse_args()

    _setup_django()
    from django.contrib.auth import get_user_model
    User = get_user_model()

    if args.count is not None and args.count > 0:
        targets = [
            (f"dummy_{secrets.token_hex(4)}@example.com", _random_full_name())
            for _ in range(args.count)
        ]
    else:
        email = args.email or f"testuser_{secrets.token_hex(4)}@example.com"
        full_name = args.full_name or "Test User"
        targets = [(email, full_name)]

    created = []
    for email, full_name in targets:
        password = SIMPLE_PASSWORD if args.simple_password else _generate_password()
        result = _create_one(User, email, full_name, password)
        if result is not None:
            created.append((*result, full_name))

    if not created:
        print("No users were created.", file=sys.stderr)
        return 1

    print(f"Created {len(created)} user(s):")
    print("-" * 72)
    for uid, email, password, full_name in created:
        print(f"ID:       {uid}")
        print(f"Name:     {full_name}")
        print(f"Email:    {email}")
        print(f"Password: {password}")
        print("-" * 72)
    print("Remember to delete this script after use.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
