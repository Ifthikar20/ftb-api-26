"""
seed_demo_data — Create the two baseline demo accounts.

Both users are intentionally created in a FRESH state — no website,
no subscription, no audits, no analytics. That way every account
(demo, admin, anything created via scripts/create_user.sh) walks the
same funnel on first login:

    login -> onboarding modal -> paywall -> dashboard

The fully-populated 'demo data' loops (audits, leads, analytics,
prompts, brands, drafts, integrations, notifications, etc.) that
used to live here have been removed. They were tied to a pre-seeded
Website + Subscription, which meant the demo user skipped both
gates of the funnel and the auto-login from run_dev.sh landed on a
populated dashboard instead of step 1.

Usage:  python manage.py seed_demo_data --settings=config.settings.dev
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Seeds the admin + demo accounts. Both start with no website / no subscription."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding demo accounts..."))

        from apps.accounts.models import User

        admin, _ = User.objects.get_or_create(
            email="admin@cansee.ai",
            defaults={
                "full_name": "Admin User",
                "company_name": "Cansee",
                "is_staff": True,
                "is_superuser": True,
                "is_email_verified": True,
            },
        )
        admin.set_password("AdminPass123!")
        admin.save()

        demo, _ = User.objects.get_or_create(
            email="demo@example.com",
            defaults={
                "full_name": "Demo User",
                "company_name": "Acme Corp",
                "is_email_verified": True,
            },
        )
        demo.set_password("DemoPass123!")
        demo.save()

        self.stdout.write(self.style.SUCCESS(
            "  ✓ admin@cansee.ai / AdminPass123!"
        ))
        self.stdout.write(self.style.SUCCESS(
            "  ✓ demo@example.com  / DemoPass123!"
        ))
        self.stdout.write("")
        self.stdout.write(self.style.NOTICE(
            "Both accounts start with no website and no subscription —"
        ))
        self.stdout.write(self.style.NOTICE(
            "they'll walk the onboarding -> paywall -> dashboard funnel on first login."
        ))
