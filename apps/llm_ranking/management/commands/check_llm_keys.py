"""Verify configured LLM provider keys with a single cheap live call each.

Usage:
    python manage.py check_llm_keys
    python manage.py check_llm_keys --provider claude

Makes one tiny request per configured provider so you can confirm a key
works (and which cheap model it resolves to) without running a full audit
or guessing why a scan 401s.
"""
from django.core.management.base import BaseCommand

from apps.llm_ranking.providers import PROVIDERS, get_provider


class Command(BaseCommand):
    help = "Ping each configured LLM provider with one cheap request."

    def add_arguments(self, parser):
        parser.add_argument(
            "--provider",
            help="Only check this provider key (e.g. claude, gpt4, gemini).",
        )

    def handle(self, *args, **options):
        only = options.get("provider")
        keys = [only] if only else list(PROVIDERS.keys())

        for key in keys:
            provider = get_provider(key)
            if provider is None:
                self.stdout.write(f"{key:12} skip    not registered")
                continue
            if not provider.is_configured():
                self.stdout.write(
                    self.style.WARNING(f"{key:12} skip    no API key configured")
                )
                continue

            model = getattr(provider, "model", "?")
            result = provider.query("Reply with the single word: ok")
            if result.succeeded:
                preview = (result.text or "").strip().replace("\n", " ")[:40]
                self.stdout.write(
                    self.style.SUCCESS(
                        f"{key:12} ok      model={model} "
                        f"tokens={result.total_tokens} reply={preview!r}"
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f"{key:12} FAIL    model={model} error={result.error[:120]}"
                    )
                )
