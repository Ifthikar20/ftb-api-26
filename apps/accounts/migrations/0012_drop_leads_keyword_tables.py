from django.db import migrations


# Drops tables for the retired `leads` and `social_leads` apps and the
# keyword-tracking models from `analytics`. Idempotent: safe on a DB where
# the tables were never created or have already been dropped.
DROP_SQL = """
DROP TABLE IF EXISTS leads_leademail            CASCADE;
DROP TABLE IF EXISTS leads_leadnote             CASCADE;
DROP TABLE IF EXISTS leads_leadsegment          CASCADE;
DROP TABLE IF EXISTS leads_scoringconfig        CASCADE;
DROP TABLE IF EXISTS leads_lead                 CASCADE;

DROP TABLE IF EXISTS social_leads_lead          CASCADE;
DROP TABLE IF EXISTS social_leads_source        CASCADE;

DROP TABLE IF EXISTS analytics_keywordalertevent CASCADE;
DROP TABLE IF EXISTS analytics_keywordalert     CASCADE;
DROP TABLE IF EXISTS analytics_keywordrankhistory CASCADE;
DROP TABLE IF EXISTS analytics_trackedkeyword   CASCADE;
DROP TABLE IF EXISTS analytics_keywordscanconfig CASCADE;
DROP TABLE IF EXISTS analytics_platformcontent  CASCADE;

DELETE FROM django_migrations WHERE app IN ('leads', 'social_leads');
"""

NOOP_SQL = "SELECT 1;"


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0011_drop_competitors_compliance_tables"),
    ]

    operations = [
        migrations.RunSQL(sql=DROP_SQL, reverse_sql=NOOP_SQL),
    ]
