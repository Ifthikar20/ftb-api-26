from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("llm_ranking", "0003_llmrankingaudit_location_and_more"),
    ]

    operations = [
        # Audit-level statistics and extraction config
        migrations.AddField(
            model_name="llmrankingaudit",
            name="runs_per_query",
            field=models.IntegerField(default=1),
        ),
        migrations.AddField(
            model_name="llmrankingaudit",
            name="mention_rate_ci_lower",
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name="llmrankingaudit",
            name="mention_rate_ci_upper",
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name="llmrankingaudit",
            name="extraction_method",
            field=models.CharField(
                choices=[
                    ("heuristic", "Heuristic (regex + lexicon)"),
                    ("llm", "LLM (Haiku-class model)"),
                ],
                default="heuristic",
                max_length=20,
            ),
        ),
        # Per-result extraction outputs
        migrations.AddField(
            model_name="llmrankingresult",
            name="run_id",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="llmrankingresult",
            name="is_linked",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="llmrankingresult",
            name="competitors_mentioned",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="llmrankingresult",
            name="primary_recommendation",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name="llmrankingresult",
            name="citations",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="llmrankingresult",
            name="extraction_model",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="llmrankingresult",
            name="extraction_version",
            field=models.CharField(blank=True, max_length=20),
        ),
    ]
