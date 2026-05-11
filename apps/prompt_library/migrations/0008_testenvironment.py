import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("websites", "0005_add_description_and_topics"),
        ("prompt_library", "0007_merge_template_fields_and_excerpt"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TestEnvironment",
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
                ("name", models.CharField(max_length=120)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_test_environments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "prompts",
                    models.ManyToManyField(
                        blank=True,
                        related_name="test_environments",
                        to="prompt_library.brandprompt",
                    ),
                ),
                (
                    "website",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="test_environments",
                        to="websites.website",
                    ),
                ),
            ],
            options={
                "db_table": "prompt_library_testenvironment",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(
                        fields=["website", "-created_at"],
                        name="pl_testenv_w_ca_idx",
                    )
                ],
                "unique_together": {("website", "name")},
            },
        ),
    ]
