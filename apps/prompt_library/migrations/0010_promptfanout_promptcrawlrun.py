import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("websites", "0005_add_description_and_topics"),
        ("prompt_library", "0009_rejectedbrandprompt"),
    ]

    operations = [
        migrations.CreateModel(
            name="PromptFanout",
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
                ("text", models.TextField()),
                ("provider", models.CharField(blank=True, max_length=24)),
                (
                    "source",
                    models.CharField(
                        choices=[("crawler", "Crawler"), ("manual", "Manual")],
                        default="crawler",
                        max_length=16,
                    ),
                ),
                ("confidence", models.FloatField(default=0.5)),
                (
                    "prompt",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="fanouts",
                        to="prompt_library.prompt",
                    ),
                ),
                (
                    "website",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="prompt_fanouts",
                        to="websites.website",
                    ),
                ),
            ],
            options={
                "db_table": "prompt_library_promptfanout",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(
                        fields=["website", "prompt", "-created_at"],
                        name="prompt_libr_website_a4f2b1_idx",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="PromptCrawlRun",
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
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("running", "Running"),
                            ("complete", "Complete"),
                            ("failed", "Failed"),
                        ],
                        default="pending",
                        max_length=12,
                    ),
                ),
                ("providers", models.JSONField(blank=True, default=list)),
                ("fanout_count", models.IntegerField(default=0)),
                ("source_count", models.IntegerField(default=0)),
                ("error", models.TextField(blank=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "prompt",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="crawl_runs",
                        to="prompt_library.prompt",
                    ),
                ),
                (
                    "website",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="prompt_crawl_runs",
                        to="websites.website",
                    ),
                ),
            ],
            options={
                "db_table": "prompt_library_promptcrawlrun",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(
                        fields=["website", "prompt", "-created_at"],
                        name="prompt_libr_website_b9c4d2_idx",
                    ),
                ],
            },
        ),
    ]
