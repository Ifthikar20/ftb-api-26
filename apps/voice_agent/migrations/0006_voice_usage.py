import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("voice_agent", "0005_calllog_lead_detection"),
        ("websites", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="calllog",
            name="billable_seconds",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="calllog",
            name="stt_seconds",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="calllog",
            name="tts_characters",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="calllog",
            name="llm_input_tokens",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="calllog",
            name="llm_output_tokens",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="calllog",
            name="estimated_cost_usd",
            field=models.DecimalField(
                decimal_places=4,
                default=0,
                help_text="Per-call cost estimate computed from per-meter unit prices.",
                max_digits=8,
            ),
        ),
        migrations.CreateModel(
            name="VoiceUsageMonthly",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("year_month", models.CharField(help_text="ISO month, e.g. '2026-04'.", max_length=7)),
                ("total_calls", models.PositiveIntegerField(default=0)),
                ("inbound_calls", models.PositiveIntegerField(default=0)),
                ("outbound_calls", models.PositiveIntegerField(default=0)),
                ("total_seconds", models.PositiveIntegerField(default=0)),
                ("billable_minutes", models.PositiveIntegerField(default=0)),
                ("llm_input_tokens", models.PositiveBigIntegerField(default=0)),
                ("llm_output_tokens", models.PositiveBigIntegerField(default=0)),
                ("tts_characters", models.PositiveBigIntegerField(default=0)),
                ("estimated_cost_usd", models.DecimalField(decimal_places=4, default=0, max_digits=10)),
                ("website", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="voice_usage_months",
                    to="websites.website",
                )),
            ],
            options={
                "db_table": "voice_agent_usage_monthly",
                "ordering": ["-year_month"],
                "unique_together": {("website", "year_month")},
                "indexes": [
                    models.Index(fields=["website", "year_month"], name="va_usage_web_ym_idx"),
                ],
            },
        ),
    ]
