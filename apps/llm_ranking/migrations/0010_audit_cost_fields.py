from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("llm_ranking", "0009_add_audit_logs"),
    ]

    operations = [
        migrations.AddField(
            model_name="llmrankingaudit",
            name="total_tokens",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="llmrankingaudit",
            name="total_cost_usd",
            field=models.DecimalField(decimal_places=6, default=0, max_digits=10),
        ),
    ]
