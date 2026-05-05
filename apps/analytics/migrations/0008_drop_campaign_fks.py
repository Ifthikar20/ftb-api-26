from django.db import migrations


class Migration(migrations.Migration):
    """
    Drop the FKs on TrackedLink and LinkClick that pointed at the
    retired email-campaign models in apps.leads. Removing the model
    fields requires a state-only operation (the columns are dropped
    by the actual SQL ALTER TABLE in the next migration).
    """

    dependencies = [
        ("analytics", "0007_rename_analytics_plat_website_platform_idx_analytics_p_website_825adc_idx_and_more"),
        ("leads", "0004_add_campaign_name_and_sender_fields"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="trackedlink",
            name="campaign",
        ),
        migrations.RemoveField(
            model_name="linkclick",
            name="campaign_recipient",
        ),
    ]
