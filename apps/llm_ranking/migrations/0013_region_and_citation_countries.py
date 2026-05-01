from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("llm_ranking", "0012_brand_strengths_and_smoothed_rate"),
    ]

    operations = [
        migrations.AddField(
            model_name="llmrankingaudit",
            name="region",
            field=models.CharField(db_index=True, default="global", max_length=10),
        ),
        migrations.AddField(
            model_name="llmrankingaudit",
            name="citation_countries",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="llmrankingresult",
            name="citation_countries",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
