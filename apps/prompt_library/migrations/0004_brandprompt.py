"""Add BrandPrompt — links a Website to a library Prompt."""
import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("prompt_library", "0003_auto_phase2_drift"),
        ("websites", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="BrandPrompt",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("notes", models.TextField(blank=True)),
                (
                    "prompt",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="brand_prompts",
                        to="prompt_library.prompt",
                    ),
                ),
                (
                    "website",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="brand_prompts",
                        to="websites.website",
                    ),
                ),
            ],
            options={
                "db_table": "prompt_library_brandprompt",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="brandprompt",
            index=models.Index(
                fields=["website", "-created_at"],
                name="prompt_libr_website_c11e98_idx",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="brandprompt",
            unique_together={("website", "prompt")},
        ),
    ]
