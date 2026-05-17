from django.db import migrations


class Migration(migrations.Migration):
    """
    Drop the publishing + ROI tables. Content Studio no longer publishes
    to third-party CMSes or tracks per-draft visibility lift; drafts
    terminate at the `approved` state in DraftStatus.
    """

    dependencies = [
        ("content_studio", "0002_drop_claim_mismatch_fk"),
    ]

    operations = [
        migrations.DeleteModel(name="ROIAttribution"),
        migrations.DeleteModel(name="PublishLog"),
        migrations.DeleteModel(name="PublishTarget"),
    ]
