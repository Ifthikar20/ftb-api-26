from django.db import migrations


# Drops tables for the retired `competitors` and `compliance` apps.
# Both apps have been removed entirely from the codebase. Idempotent:
# safe on a DB where the tables were never created or already dropped.
DROP_SQL = """
DROP TABLE IF EXISTS competitors_competitorchange   CASCADE;
DROP TABLE IF EXISTS competitors_keywordgap         CASCADE;
DROP TABLE IF EXISTS competitors_competitorsnapshot CASCADE;
DROP TABLE IF EXISTS competitors_competitor        CASCADE;
DROP TABLE IF EXISTS compliance_audit_log          CASCADE;
DELETE FROM django_migrations WHERE app IN ('competitors', 'compliance');
"""

NOOP_SQL = "SELECT 1;"


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0010_drop_campaign_tables"),
    ]

    operations = [
        migrations.RunSQL(sql=DROP_SQL, reverse_sql=NOOP_SQL),
    ]
