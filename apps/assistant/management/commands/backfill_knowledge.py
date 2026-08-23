"""Seed the unified knowledge corpus from existing rows.

Runs the Phase 2 producer adapters synchronously, so the assistant can
answer historical questions without waiting for new events (and without
a Celery worker, which does not run locally).

Usage:
    manage.py backfill_knowledge                      # every active website
    manage.py backfill_knowledge --website <uuid>     # one website
    manage.py backfill_knowledge --email user@x.com   # one account
"""
from django.core.management.base import BaseCommand

from apps.assistant.services import producers
from apps.websites.models import Website


class Command(BaseCommand):
    help = "Backfill the assistant's unified knowledge corpus from existing data."

    def add_arguments(self, parser):
        parser.add_argument("--website", help="Only this website id.")
        parser.add_argument("--email", help="Only websites owned by this user.")

    def handle(self, *args, **options):
        qs = Website.objects.select_related("user").filter(is_active=True)
        if options.get("website"):
            qs = qs.filter(id=options["website"])
        if options.get("email"):
            qs = qs.filter(user__email__iexact=options["email"])

        websites = list(qs)
        if not websites:
            self.stdout.write(self.style.WARNING("No matching websites."))
            return

        totals = {}
        for website in websites:
            counts = producers.sync_website(website)
            for key, value in counts.items():
                totals[key] = totals.get(key, 0) + value
            summary = ", ".join(f"{k}={v}" for k, v in counts.items())
            self.stdout.write(f"{website.name or website.url}: {summary}")

        detail = ", ".join(f"{k}={v}" for k, v in totals.items())
        self.stdout.write(self.style.SUCCESS(
            f"Backfilled {len(websites)} website(s): {detail}"
        ))
