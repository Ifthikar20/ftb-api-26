"""Initial schema for the claim_verifier app."""
import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("websites", "0001_initial"),
        ("llm_ranking", "0015_prompt_source_fields"),
        ("brand_vault", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Claim",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("text", models.TextField()),
                ("subject", models.CharField(blank=True, max_length=300)),
                ("predicate", models.CharField(blank=True, max_length=200)),
                ("object", models.TextField(blank=True)),
                ("confidence", models.FloatField(default=0.5)),
                ("embedding", models.JSONField(blank=True, null=True)),
                ("audit", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="claims", to="llm_ranking.llmrankingaudit",
                )),
                ("result", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="claims", to="llm_ranking.llmrankingresult",
                )),
                ("website", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="claims", to="websites.website",
                )),
            ],
            options={"db_table": "claim_verifier_claim"},
        ),
        migrations.AddIndex(
            model_name="claim",
            index=models.Index(fields=["website", "audit"], name="cv_claim_w_a_idx"),
        ),
        migrations.AddIndex(
            model_name="claim",
            index=models.Index(fields=["audit", "result"], name="cv_claim_a_r_idx"),
        ),
        migrations.CreateModel(
            name="ClaimMismatch",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("mismatch_type", models.CharField(
                    choices=[
                        ("contradicts", "Contradicts"),
                        ("outdated", "Outdated"),
                        ("unknown", "Unknown"),
                        ("partial", "Partial"),
                    ],
                    max_length=16,
                )),
                ("severity", models.CharField(
                    choices=[
                        ("critical", "Critical"),
                        ("high", "High"),
                        ("medium", "Medium"),
                        ("low", "Low"),
                        ("info", "Info"),
                    ],
                    default="medium", max_length=12,
                )),
                ("factual_divergence", models.FloatField(default=0.5)),
                ("audience_reach", models.FloatField(default=0.5)),
                ("explanation", models.TextField(blank=True)),
                ("dismissed", models.BooleanField(default=False)),
                ("dismissed_at", models.DateTimeField(blank=True, null=True)),
                ("claim", models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="mismatch", to="claim_verifier.claim",
                )),
                ("matched_fact", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="mismatches", to="brand_vault.brandfact",
                )),
            ],
            options={"db_table": "claim_verifier_claimmismatch"},
        ),
        migrations.AddIndex(
            model_name="claimmismatch",
            index=models.Index(fields=["claim"], name="cv_mm_claim_idx"),
        ),
        migrations.AddIndex(
            model_name="claimmismatch",
            index=models.Index(fields=["matched_fact"], name="cv_mm_fact_idx"),
        ),
        migrations.AddIndex(
            model_name="claimmismatch",
            index=models.Index(fields=["severity", "mismatch_type"], name="cv_mm_sev_typ_idx"),
        ),
    ]
