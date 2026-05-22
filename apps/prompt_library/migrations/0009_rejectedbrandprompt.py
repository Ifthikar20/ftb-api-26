import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("websites", "0005_add_description_and_topics"),
        ("prompt_library", "0008_testenvironment"),
    ]

    operations = [
        migrations.CreateModel(
            name="RejectedBrandPrompt",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
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
                (
                    "prompt",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="rejections",
                        to="prompt_library.prompt",
                    ),
                ),
                (
                    "website",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="rejected_prompts",
                        to="websites.website",
                    ),
                ),
            ],
            options={
                "db_table": "prompt_library_rejectedbrandprompt",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(
                        fields=["website", "-created_at"],
                        name="prompt_libr_website_3a8e91_idx",
                    ),
                ],
                "unique_together": {("website", "prompt")},
            },
        ),
    ]
