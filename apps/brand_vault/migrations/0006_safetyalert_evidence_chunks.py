from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("brand_vault", "0005_safetyprompt_agent_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="safetyalert",
            name="evidence_chunks",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
