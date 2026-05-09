"""Phase 3: templated prompts, effectiveness fields, per-website variables.

Adds template fields to :class:`Prompt` and a new
:class:`PromptVariableSet` model so each website can supply a
dictionary of values that fill the {{ variable }} slots in a template.
"""
import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("prompt_library", "0003_auto_phase2_drift"),
        ("websites", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="prompt",
            name="template_text",
            field=models.TextField(
                blank=True,
                help_text="Prompt body with {{ variable }} placeholders. If empty, falls back to text.",
            ),
        ),
        migrations.AddField(
            model_name="prompt",
            name="template_variables",
            field=models.JSONField(
                default=list,
                blank=True,
                help_text="Auto-extracted list of placeholder names",
            ),
        ),
        migrations.AddField(
            model_name="prompt",
            name="style",
            field=models.CharField(
                choices=[
                    ("question", "Question"),
                    ("story", "Story"),
                    ("comparison", "Comparison"),
                    ("local", "Local"),
                    ("how_to", "How-to"),
                    ("listicle", "Listicle"),
                ],
                db_index=True,
                default="question",
                max_length=24,
            ),
        ),
        migrations.AddField(
            model_name="prompt",
            name="effectiveness_score",
            field=models.FloatField(
                db_index=True,
                default=0.0,
                help_text="Cached 0-1 score from past audit performance",
            ),
        ),
        migrations.AddField(
            model_name="prompt",
            name="effectiveness_components",
            field=models.JSONField(
                default=dict,
                blank=True,
                help_text="Per-axis breakdown: visibility_hit_rate, citation_yield, claim_yield, coverage_breadth",
            ),
        ),
        migrations.AddField(
            model_name="prompt",
            name="runs_count",
            field=models.IntegerField(
                default=0,
                help_text="Number of audit runs that used this prompt",
            ),
        ),
        migrations.AddField(
            model_name="prompt",
            name="last_used_at",
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.CreateModel(
            name="PromptVariableSet",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False,
                    ),
                ),
                (
                    "variables",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="key -> value, e.g. {'location': 'Dallas', 'sales_item': 'medical board'}",
                    ),
                ),
                (
                    "website",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="prompt_variables",
                        to="websites.website",
                    ),
                ),
            ],
            options={"db_table": "prompt_library_promptvariableset"},
        ),
    ]
