from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Initial migration for the stub `leads` app. The two models exist
    only to satisfy historical lazy ForeignKey references in
    `analytics` migrations (FKs were removed in analytics.0008).
    Both are `managed = False`, so no DDL is emitted.
    """

    initial = True

    dependencies = [
        # Run after the SQL drop of any legacy leads_* tables, so the
        # django_migrations DELETE in that migration cannot remove this row.
        ("accounts", "0012_drop_leads_keyword_tables"),
    ]

    operations = [
        migrations.CreateModel(
            name="EmailCampaign",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
            ],
            options={"db_table": "leads_emailcampaign", "managed": False},
        ),
        migrations.CreateModel(
            name="CampaignRecipient",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
            ],
            options={"db_table": "leads_campaignrecipient", "managed": False},
        ),
    ]
