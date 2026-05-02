from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("llm_ranking", "0011_result_prompt_index_unique"),
    ]

    operations = [
        migrations.AddField(
            model_name="llmrankingaudit",
            name="mention_rate_smoothed",
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name="llmrankingaudit",
            name="brand_strengths",
            field=models.JSONField(default=dict, blank=True),
        ),
    ]
