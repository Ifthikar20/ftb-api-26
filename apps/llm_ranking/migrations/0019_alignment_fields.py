"""Brand alignment benchmark fields.

Per-result score + capped detail + version stamps (mirroring the
extraction_model/extraction_version convention), plus a display-only
mean on the audit.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("llm_ranking", "0018_result_public_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="llmrankingresult",
            name="alignment_score",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="llmrankingresult",
            name="alignment_detail",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="llmrankingresult",
            name="alignment_model",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="llmrankingresult",
            name="alignment_version",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name="llmrankingaudit",
            name="alignment_score",
            field=models.FloatField(blank=True, null=True),
        ),
    ]
