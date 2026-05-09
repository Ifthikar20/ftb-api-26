"""Seed the 20-industry flat taxonomy used by the prompt library."""
from django.db import migrations
from django.utils.text import slugify


INDUSTRIES = [
    "SaaS / Analytics",
    "SaaS / CRM",
    "SaaS / DevTools",
    "E-commerce / DTC",
    "E-commerce / Marketplaces",
    "Local Services / HVAC",
    "Local Services / Home Services",
    "Local Services / Health & Wellness",
    "Financial Services",
    "Insurance",
    "Legal Services",
    "Education / EdTech",
    "Real Estate",
    "Hospitality / Travel",
    "Food & Beverage",
    "Media / Publishing",
    "Healthcare / Telemedicine",
    "Manufacturing / Industrial",
    "Nonprofit",
    "Professional Services / Consulting",
]


def seed_forwards(apps, schema_editor):
    Industry = apps.get_model("prompt_library", "Industry")
    for name in INDUSTRIES:
        slug = slugify(name)[:64]
        Industry.objects.update_or_create(
            slug=slug, defaults={"name": name, "is_active": True}
        )


def seed_reverse(apps, schema_editor):
    Industry = apps.get_model("prompt_library", "Industry")
    slugs = [slugify(name)[:64] for name in INDUSTRIES]
    Industry.objects.filter(slug__in=slugs).delete()


class Migration(migrations.Migration):

    dependencies = [("prompt_library", "0001_initial")]
    operations = [migrations.RunPython(seed_forwards, seed_reverse)]
