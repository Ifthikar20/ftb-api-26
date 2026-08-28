"""
Create a real user directly in the production database so they can log in
at https://cansee.ai/login immediately (no email verification step).

Run from the prod host (same place ``python manage.py shell`` would work)
where DATABASE_URL and the rest of the prod env are already exported:

    # Single user, explicit password
    DJANGO_SETTINGS_MODULE=config.settings.prod \\
        python scripts/create_prod_user.py user@example.com "Jane Doe" --password 'S3cretPass!'

    # Single user, auto-generated password (printed at the end)
    DJANGO_SETTINGS_MODULE=config.settings.prod \\
        python scripts/create_prod_user.py user@example.com "Jane Doe"

    # Batch from a CSV file with columns: email,full_name[,password]
    DJANGO_SETTINGS_MODULE=config.settings.prod \\
        python scripts/create_prod_user.py --csv users.csv

Safety:
    The script refuses to run unless ``DJANGO_SETTINGS_MODULE`` ends in
    ``.prod``. Pass --yes to skip the interactive confirmation (useful
    when piping or running from CI).
"""

from __future__ import annotations

import argparse
import csv
import os
import secrets
import string
import sys

import django


def _setup_django() -> None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")
    django.setup()


def _generate_password(length: int = 20) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        pw = "".join(secrets.choice(alphabet) for _ in range(length))
        # Ensure the generated password satisfies common validators
        if (
            any(c.islower() for c in pw)
            and any(c.isupper() for c in pw)
            and any(c.isdigit() for c in pw)
        ):
            return pw


def _create_one(
    User,
    email: str,
    full_name: str,
    password: str,
    *,
    plan: str | None,
    is_staff: bool,
) -> tuple[str, str, str, str] | None:
    email = email.strip().lower()
    full_name = (full_name or "").strip() or email.split("@", 1)[0]

    if User.objects.filter(email__iexact=email).exists():
        print(f"SKIP: {email} already exists.", file=sys.stderr)
        return None

    extra: dict = {
        "full_name": full_name,
        "is_email_verified": True,
        "is_active": True,
        "is_staff": is_staff,
    }
    if plan:
        extra["plan"] = plan

    user = User.objects.create_user(email=email, password=password, **extra)
    return str(user.id), user.email, password, full_name


def _read_csv(path: str) -> list[tuple[str, str, str | None]]:
    rows: list[tuple[str, str, str | None]] = []
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames or "email" not in {
            (f or "").strip().lower() for f in reader.fieldnames
        }:
            # Fall back to positional columns
            fh.seek(0)
            for raw in csv.reader(fh):
                if not raw or not raw[0].strip():
                    continue
                email = raw[0].strip()
                name = raw[1].strip() if len(raw) > 1 else ""
                pw = raw[2].strip() if len(raw) > 2 and raw[2].strip() else None
                rows.append((email, name, pw))
            return rows
        for row in reader:
            email = (row.get("email") or "").strip()
            if not email:
                continue
            name = (row.get("full_name") or row.get("name") or "").strip()
            pw = (row.get("password") or "").strip() or None
            rows.append((email, name, pw))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create production users that can log in immediately.",
    )
    parser.add_argument("email", nargs="?", help="Email for a single user.")
    parser.add_argument("full_name", nargs="?", help="Full name for a single user.")
    parser.add_argument("--password", "-p", default=None, help="Explicit password (single-user mode).")
    parser.add_argument("--csv", default=None, help="Bulk-create from CSV (columns: email,full_name[,password]).")
    parser.add_argument("--plan", default=None, help="Override plan (e.g. individual, growth, enterprise).")
    parser.add_argument("--staff", action="store_true", help="Mark the user(s) as Django staff (admin access).")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip the prod confirmation prompt.")
    args = parser.parse_args()

    settings_module = os.environ.get("DJANGO_SETTINGS_MODULE", "")
    if not settings_module.endswith(".prod"):
        print(
            f"Refusing to run: DJANGO_SETTINGS_MODULE={settings_module!r} is not a prod settings module.\n"
            "Re-run with DJANGO_SETTINGS_MODULE=config.settings.prod",
            file=sys.stderr,
        )
        return 2

    if not args.yes:
        confirm = input(
            "About to create user(s) in PRODUCTION. Type 'CREATE' to continue: "
        ).strip()
        if confirm != "CREATE":
            print("Aborted.", file=sys.stderr)
            return 1

    _setup_django()
    from django.contrib.auth import get_user_model
    User = get_user_model()

    # Build the list of (email, full_name, password) to create.
    targets: list[tuple[str, str, str | None]] = []
    if args.csv:
        targets = _read_csv(args.csv)
        if not targets:
            print(f"No rows found in {args.csv}.", file=sys.stderr)
            return 1
    else:
        if not args.email:
            parser.error("email is required when --csv is not used.")
        targets = [(args.email, args.full_name or "", args.password)]

    created: list[tuple[str, str, str, str]] = []
    for email, full_name, explicit_pw in targets:
        password = explicit_pw or _generate_password()
        row = _create_one(
            User,
            email,
            full_name,
            password,
            plan=args.plan,
            is_staff=args.staff,
        )
        if row is not None:
            created.append(row)

    if not created:
        print("No users were created.", file=sys.stderr)
        return 1

    print(f"Created {len(created)} user(s). They can log in now at https://cansee.ai/login")
    print("-" * 72)
    for uid, email, password, full_name in created:
        print(f"ID:       {uid}")
        print(f"Name:     {full_name}")
        print(f"Email:    {email}")
        print(f"Password: {password}")
        print("-" * 72)
    print(
        "Store these credentials in a password manager and share them over a "
        "secure channel. The plaintext password is not recoverable later."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
