from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("voice_agent", "0004_phone_mfa_and_always_on"),
    ]

    operations = [
        migrations.AddField(
            model_name="calllog",
            name="is_possible_lead",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name="calllog",
            name="lead_score",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="calllog",
            name="lead_signals",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text=(
                    "Per-signal contributions used to compute lead_score "
                    "(for explainability)."
                ),
            ),
        ),
        migrations.AddField(
            model_name="calllog",
            name="lead_promoted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="calllog",
            name="lead_dismissed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
