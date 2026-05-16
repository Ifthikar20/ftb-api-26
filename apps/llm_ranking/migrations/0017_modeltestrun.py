"""Persist Model Test runs.

Add the ``ModelTestRun`` table so the lightweight Model Test probe is
no longer ephemeral. The Redis state remains the source of truth while
the worker is running; this row is written once at the end so users
can re-open historical runs after the 1h TTL has elapsed.
"""
import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("llm_ranking", "0016_result_source_prompt"),
        ("websites", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ModelTestRun",
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
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("queued", "Queued"),
                            ("running", "Running"),
                            ("analyzing", "Analyzing"),
                            ("complete", "Complete"),
                            ("failed", "Failed"),
                        ],
                        db_index=True,
                        default="complete",
                        max_length=20,
                    ),
                ),
                ("prompts", models.JSONField(default=list)),
                ("providers", models.JSONField(default=list)),
                ("brand_terms", models.JSONField(default=list)),
                ("prompt_rows", models.JSONField(blank=True, default=list)),
                ("summary", models.JSONField(blank=True, default=dict)),
                ("analysis", models.JSONField(blank=True, null=True)),
                ("analysis_status", models.CharField(blank=True, max_length=20)),
                ("analysis_error", models.TextField(blank=True)),
                ("google_grounding", models.JSONField(blank=True, null=True)),
                ("grounding_status", models.CharField(blank=True, max_length=20)),
                ("grounding_error", models.TextField(blank=True)),
                ("total_calls", models.IntegerField(default=0)),
                ("completed_calls", models.IntegerField(default=0)),
                ("error_message", models.TextField(blank=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("duration_seconds", models.FloatField(blank=True, null=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="model_test_runs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "website",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="model_test_runs",
                        to="websites.website",
                    ),
                ),
            ],
            options={
                "db_table": "llm_ranking_model_test_run",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(
                        fields=["website", "-created_at"],
                        name="llm_ranking_model_t_website_created_idx",
                    ),
                    models.Index(
                        fields=["status"],
                        name="llm_ranking_model_t_status_idx",
                    ),
                ],
            },
        ),
    ]
