from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("brand_vault", "0004_brandsecurityagent_brandsecurityconfig_and_more"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="safetyprompt",
            unique_together=set(),
        ),
        migrations.AddField(
            model_name="safetyprompt",
            name="agent_id",
            field=models.CharField(default="llm_truth", max_length=40),
        ),
        migrations.AlterUniqueTogether(
            name="safetyprompt",
            unique_together={("website", "agent_id", "text")},
        ),
        migrations.AddIndex(
            model_name="safetyprompt",
            index=models.Index(
                fields=["website", "agent_id", "status"],
                name="bv_sp_w_a_s_idx",
            ),
        ),
    ]
