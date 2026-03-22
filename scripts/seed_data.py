#!/usr/bin/env python
"""
Development seed data script.
Run: python scripts/seed_data.py
"""
import os
import sys

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

from apps.accounts.models import User  # noqa: E402
from apps.websites.models import Website, WebsiteSettings  # noqa: E402


def seed():
    print("Seeding development data...")

    # Create admin user
    admin, created = User.objects.get_or_create(
        email="admin@growthpilot.io",
        defaults={
            "full_name": "Admin User",
            "company_name": "GrowthPilot",
            "plan": "scale",
            "is_staff": True,
            "is_superuser": True,
            "is_email_verified": True,
        },
    )
    if created:
        admin.set_password("AdminPass123!")
        admin.save()
        print(f"  Created admin: {admin.email}")
    else:
        print(f"  Admin already exists: {admin.email}")

    # Create demo user
    demo, created = User.objects.get_or_create(
        email="demo@example.com",
        defaults={
            "full_name": "Demo User",
            "company_name": "Acme Corp",
            "plan": "growth",
            "is_email_verified": True,
        },
    )
    if created:
        demo.set_password("DemoPass123!")
        demo.save()
        print(f"  Created demo user: {demo.email}")

    # Create demo website
    website, created = Website.objects.get_or_create(
        user=demo,
        url="https://demo.example.com",
        defaults={"name": "Demo Website", "industry": "SaaS"},
    )
    if created:
        WebsiteSettings.objects.get_or_create(website=website)
        print(f"  Created website: {website.name}")

    print("Seed complete!")


if __name__ == "__main__":
    seed()
