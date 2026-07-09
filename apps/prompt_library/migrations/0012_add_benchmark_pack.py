"""Benchmark packs: reference material + Claude-extracted claims.

The `Rename index` / `Alter field created_at` operations Django would
otherwise generate for existing tables are index-name drift from
earlier merges and add no schema change on Postgres. Leaving them out
keeps this migration focused on the two new tables so a rollback is
straightforward.
"""
import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
        ("prompt_library", "0011_brandprompt_tags_location"),
        ("websites", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="BenchmarkPack",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "source_kind",
                    models.CharField(
                        choices=[("url", "URL"), ("markdown", "Markdown")],
                        max_length=16,
                    ),
                ),
                ("label", models.CharField(max_length=500)),
                ("url", models.URLField(blank=True, max_length=2000)),
                ("markdown_content", models.TextField(blank=True)),
                ("fetched_title", models.CharField(blank=True, max_length=500)),
                ("fetched_summary", models.TextField(blank=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("extracting", "Extracting"),
                            ("ready", "Ready"),
                            ("failed", "Failed"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=16,
                    ),
                ),
                ("extraction_error", models.TextField(blank=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="benchmark_packs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "website",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="benchmark_packs",
                        to="websites.website",
                    ),
                ),
            ],
            options={
                "db_table": "prompt_library_benchmarkpack",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="BenchmarkClaim",
            fields=[
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
                    "category",
                    models.CharField(
                        choices=[
                            ("product", "Product"),
                            ("customer", "Customer"),
                            ("pricing", "Pricing"),
                            ("feature", "Feature"),
                            ("proof", "Proof point"),
                            ("other", "Other"),
                        ],
                        default="other",
                        max_length=16,
                    ),
                ),
                ("text", models.CharField(max_length=500)),
                ("evidence", models.CharField(blank=True, max_length=500)),
                ("ordinal", models.IntegerField(default=0)),
                (
                    "pack",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="claims",
                        to="prompt_library.benchmarkpack",
                    ),
                ),
            ],
            options={
                "db_table": "prompt_library_benchmarkclaim",
                "ordering": ["ordinal", "id"],
            },
        ),
        migrations.AddIndex(
            model_name="benchmarkpack",
            index=models.Index(
                fields=["website", "-created_at"],
                name="prompt_libr_website_2c533a_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="benchmarkclaim",
            index=models.Index(
                fields=["pack", "ordinal"],
                name="prompt_libr_pack_id_65a124_idx",
            ),
        ),
    ]
