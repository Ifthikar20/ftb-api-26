"""Add SafetyPrompt and SafetyAlert models for AI Brand Safety monitoring."""
import uuid

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("websites", "0001_initial"),
        ("brand_vault", "0002_tonesample"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SafetyPrompt",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("text", models.CharField(max_length=500)),
                ("status", models.CharField(
                    choices=[("active", "Active"), ("paused", "Paused")],
                    default="active", max_length=10,
                )),
                ("created_by", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="created_safety_prompts",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("website", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="safety_prompts", to="websites.website",
                )),
            ],
            options={
                "db_table": "brand_vault_safetyprompt",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="safetyprompt",
            index=models.Index(fields=["website", "status"], name="bv_sp_w_s_idx"),
        ),
        migrations.AlterUniqueTogether(
            name="safetyprompt",
            unique_together={("website", "text")},
        ),
        migrations.CreateModel(
            name="SafetyAlert",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("model", models.CharField(max_length=40)),
                ("prompt_text", models.CharField(max_length=500)),
                ("snippet", models.TextField()),
                ("issue", models.CharField(
                    choices=[
                        ("hallucination", "Hallucination"),
                        ("unverified", "Unverified claim"),
                        ("outdated", "Outdated info"),
                        ("harmful", "Harmful mention"),
                        ("negative", "Negative mention"),
                    ],
                    max_length=20,
                )),
                ("detail", models.TextField(blank=True)),
                ("severity", models.CharField(
                    choices=[("high", "High"), ("medium", "Medium"), ("low", "Low")],
                    max_length=10,
                )),
                ("status", models.CharField(
                    choices=[("open", "Open"), ("resolved", "Resolved"), ("dismissed", "Dismissed")],
                    default="open", max_length=10,
                )),
                ("detected_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("prompt", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="alerts", to="brand_vault.safetyprompt",
                )),
                ("resolved_by", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="resolved_safety_alerts",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("website", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="safety_alerts", to="websites.website",
                )),
            ],
            options={
                "db_table": "brand_vault_safetyalert",
                "ordering": ["-detected_at"],
            },
        ),
        migrations.AddIndex(
            model_name="safetyalert",
            index=models.Index(
                fields=["website", "status", "-detected_at"],
                name="bv_sa_w_s_dt_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="safetyalert",
            index=models.Index(fields=["website", "severity"], name="bv_sa_w_sev_idx"),
        ),
    ]
