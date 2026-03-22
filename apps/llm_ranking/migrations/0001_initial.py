import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("websites", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="LLMRankingAudit",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("running", "Running"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("prompts", models.JSONField(default=list)),
                ("business_name", models.CharField(blank=True, max_length=200)),
                ("business_description", models.TextField(blank=True)),
                ("industry", models.CharField(blank=True, max_length=100)),
                ("keywords", models.JSONField(default=list)),
                ("overall_score", models.IntegerField(db_index=True, default=0)),
                ("mention_rate", models.FloatField(default=0.0)),
                ("avg_mention_rank", models.FloatField(default=0.0)),
                ("providers_queried", models.JSONField(default=list)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("error_message", models.TextField(blank=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="llm_ranking_audits",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "website",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="llm_ranking_audits",
                        to="websites.website",
                    ),
                ),
            ],
            options={"db_table": "llm_ranking_audit", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="LLMRankingResult",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "provider",
                    models.CharField(
                        choices=[
                            ("claude", "Claude (Anthropic)"),
                            ("gpt4", "GPT-4 (OpenAI)"),
                            ("gemini", "Gemini (Google)"),
                            ("perplexity", "Perplexity"),
                        ],
                        db_index=True,
                        max_length=20,
                    ),
                ),
                ("prompt", models.TextField()),
                ("response_text", models.TextField(blank=True)),
                ("is_mentioned", models.BooleanField(db_index=True, default=False)),
                ("mention_rank", models.IntegerField(blank=True, null=True)),
                (
                    "sentiment",
                    models.CharField(
                        choices=[
                            ("positive", "Positive"),
                            ("neutral", "Neutral"),
                            ("negative", "Negative"),
                            ("not_mentioned", "Not Mentioned"),
                        ],
                        default="not_mentioned",
                        max_length=20,
                    ),
                ),
                ("confidence_score", models.FloatField(default=0.0)),
                ("mention_context", models.TextField(blank=True)),
                ("query_succeeded", models.BooleanField(default=True)),
                ("error_message", models.TextField(blank=True)),
                (
                    "audit",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="results",
                        to="llm_ranking.llmrankingaudit",
                    ),
                ),
            ],
            options={"db_table": "llm_ranking_result"},
        ),
        migrations.AddIndex(
            model_name="llmrankingresult",
            index=models.Index(fields=["audit", "provider"], name="llm_result_audit_provider_idx"),
        ),
        migrations.AddIndex(
            model_name="llmrankingresult",
            index=models.Index(fields=["audit", "is_mentioned"], name="llm_result_audit_mentioned_idx"),
        ),
    ]
