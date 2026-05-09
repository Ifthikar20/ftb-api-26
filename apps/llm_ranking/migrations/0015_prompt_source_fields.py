"""Demand-side prompt provenance fields.

Adds ``prompt_source`` to :class:`LLMRankingAudit` so a run can pull
prompts from the demand-side library, the user's vault, or both, and
``prompt_source_label`` to :class:`LLMRankingResult` so the dashboard
can show provenance badges per row.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("llm_ranking", "0014_schedule_resilience"),
    ]

    operations = [
        migrations.AddField(
            model_name="llmrankingaudit",
            name="prompt_source",
            field=models.CharField(
                choices=[("vault", "vault"), ("library", "library"), ("hybrid", "hybrid")],
                default="vault",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="llmrankingresult",
            name="prompt_source_label",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
    ]
