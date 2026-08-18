"""Alert identity and lifecycle fields for the multi-detector auditor.

Step 1 of 3 (add nullable / defaulted columns). The reference column starts
nullable and non-unique so migration 0010 can assign a distinct value per
existing row before 0011 applies the unique constraint — the same 3-step
shape as llm_ranking 0018_result_public_id.
"""
from django.db import migrations, models
import django.utils.timezone

import apps.brand_vault.models


class Migration(migrations.Migration):

    dependencies = [
        ("brand_vault", "0008_safetyalert_result"),
    ]

    operations = [
        migrations.AddField(
            model_name="safetyalert",
            name="reference",
            field=models.CharField(
                default=apps.brand_vault.models.generate_alert_reference,
                editable=False,
                max_length=16,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="safetyalert",
            name="detector_code",
            field=models.CharField(blank=True, db_index=True, default="", max_length=20),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="safetyalert",
            name="evidence_spans",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="safetyalert",
            name="first_seen_at",
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name="safetyalert",
            name="last_seen_at",
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name="safetyalert",
            name="occurrence_count",
            field=models.IntegerField(default=1),
        ),
        migrations.AddField(
            model_name="safetyalert",
            name="dedupe_key",
            field=models.CharField(blank=True, db_index=True, default="", max_length=40),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="safetyalert",
            name="issue",
            field=models.CharField(
                choices=[
                    ("hallucination", "Hallucination"),
                    ("unverified", "Unverified claim"),
                    ("outdated", "Outdated info"),
                    ("harmful", "Harmful mention"),
                    ("negative", "Negative mention"),
                    ("emerging_narrative", "Emerging narrative"),
                    ("negative_outranking", "Negative page outranking"),
                    ("ranking_for_bad_query", "Ranking for negative query"),
                    ("sge_misrepresentation", "AI Overview misrepresentation"),
                    ("sentiment_drop", "Sentiment drop"),
                    ("impersonation", "Impersonation"),
                    ("derogatory", "Derogatory language"),
                    ("unfavorable_comparison", "Unfavorable comparison"),
                    ("weak_endorsement", "Weak endorsement"),
                    ("distrust", "Distrust signals"),
                ],
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="brandsecurityconfig",
            name="llm_judge_enabled",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="brandsecurityconfig",
            name="last_response_scan_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
