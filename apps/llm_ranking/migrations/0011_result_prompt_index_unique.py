from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("llm_ranking", "0010_audit_cost_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="llmrankingresult",
            name="prompt_index",
            field=models.IntegerField(default=0),
        ),
        migrations.AddConstraint(
            model_name="llmrankingresult",
            constraint=models.UniqueConstraint(
                fields=["audit", "prompt_index", "provider", "run_id"],
                name="uq_llm_result_audit_prompt_provider_run",
            ),
        ),
    ]
