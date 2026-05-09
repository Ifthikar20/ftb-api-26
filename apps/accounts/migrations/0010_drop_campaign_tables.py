from django.db import migrations


# One-shot cleanup. Drops the two leads_* tables that backed the
# retired email-campaign feature, plus their referencing index /
# constraint structures via CASCADE. Runs after:
#
#   • analytics.0008_drop_campaign_fks  (removes FK columns on
#     TrackedLink + LinkClick)
#   • leads.0005_drop_campaign_models   (removes the models from
#     migration state without issuing DROP TABLE)
#
# Idempotent: ``DROP TABLE IF EXISTS`` is safe to re-apply on a DB
# that's already had the tables dropped. CASCADE clears any residual
# FKs we missed (e.g. from a deploy that skipped 0008).
DROP_SQL = """
DROP TABLE IF EXISTS leads_campaignrecipient CASCADE;
DROP TABLE IF EXISTS leads_emailcampaign     CASCADE;
"""

NOOP_SQL = "SELECT 1;"


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0009_drop_messaging_tables"),
    ]

    operations = [
        migrations.RunSQL(sql=DROP_SQL, reverse_sql=NOOP_SQL),
    ]
