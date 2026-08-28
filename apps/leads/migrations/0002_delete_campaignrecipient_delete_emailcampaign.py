"""Drop the last two tables of the retired `leads` app.

The models were `managed = False` stubs, so ``DeleteModel`` only removes
them from Django's migration state -- it emits no DDL, which is why
``leads_emailcampaign`` and ``leads_campaignrecipient`` were still
present (empty) in the database long after the app was retired. The
explicit ``RunSQL`` below is what actually removes them.

Both tables were verified empty before this ran, and the foreign keys
that once pointed at them were dropped in
apps/analytics/migrations/0008_drop_campaign_fks.py. ``CASCADE`` is
deliberately NOT used: if some unexpected dependency still exists, this
should fail loudly rather than silently drop it.

Irreversible by design -- re-creating empty tables for a retired app
would serve no purpose, so the reverse is a no-op guarded by
``RunSQL.noop``.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('leads', '0001_initial'),
    ]

    operations = [
        migrations.DeleteModel(
            name='CampaignRecipient',
        ),
        migrations.DeleteModel(
            name='EmailCampaign',
        ),
        migrations.RunSQL(
            sql=[
                "DROP TABLE IF EXISTS leads_campaignrecipient;",
                "DROP TABLE IF EXISTS leads_emailcampaign;",
            ],
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
