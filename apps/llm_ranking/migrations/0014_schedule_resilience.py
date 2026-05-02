import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Resilience fields on LLMRankingSchedule:
      - last_audit            FK so dispatcher can skip if still running
      - consecutive_failures  count for auto-pause
      - last_failure_at       for UI triage
      - auto_pause_threshold  per-schedule cap (default 3)
    """

    dependencies = [
        ("llm_ranking", "0013_region_and_citation_countries"),
    ]

    operations = [
        migrations.AddField(
            model_name="llmrankingschedule",
            name="last_audit",
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="llm_ranking.llmrankingaudit",
            ),
        ),
        migrations.AddField(
            model_name="llmrankingschedule",
            name="consecutive_failures",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="llmrankingschedule",
            name="last_failure_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="llmrankingschedule",
            name="auto_pause_threshold",
            field=models.IntegerField(default=3),
        ),
    ]
