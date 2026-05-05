from django.db import migrations


class Migration(migrations.Migration):
    """
    Remove EmailCampaign and CampaignRecipient from the migration state.
    The corresponding tables are dropped in the next migration,
    apps.accounts.0010_drop_campaign_tables, which uses raw SQL because
    Django's DeleteModel runs SQL in the wrong order when other apps'
    FKs were just removed (we need the FKs gone before we can DROP).
    """

    dependencies = [
        ("leads", "0004_add_campaign_name_and_sender_fields"),
        # Wait for analytics to drop its FK columns first.
        ("analytics", "0008_drop_campaign_fks"),
    ]

    operations = [
        # state_operations: tell Django to forget the models exist
        # without actually issuing DROP TABLE SQL. The DROP comes via
        # accounts.0010 below, which runs after this migration.
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(name="CampaignRecipient"),
                migrations.DeleteModel(name="EmailCampaign"),
            ],
            database_operations=[],
        ),
    ]
