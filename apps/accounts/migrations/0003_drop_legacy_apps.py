"""One-shot migration that drops the database tables and django_migrations
rows for the removed `strategy`, `gamification`, and `audits` apps.

The original removal commit deleted the model code and migration files but did
not run a `migrate <app> zero` first, so production and dev databases still
hold the legacy tables. This migration finishes that cleanup.

The reverse function is a noop because the model code no longer exists and
the tables cannot be recreated from this migration alone.
"""
from django.db import migrations

LEGACY_APPS = ("strategy", "gamification", "audits")


def drop_legacy(apps, schema_editor):
    conn = schema_editor.connection
    with conn.cursor() as cur:
        existing = set(conn.introspection.table_names(cur))
        targets = sorted(
            t for t in existing
            if any(t.startswith(p + "_") for p in LEGACY_APPS)
        )
        for table in targets:
            cur.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')
        cur.execute(
            "DELETE FROM django_migrations WHERE app IN %s",
            [tuple(LEGACY_APPS)],
        )


class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_user_segment_alter_user_plan_organization_and_more")]
    operations = [migrations.RunPython(drop_legacy, migrations.RunPython.noop)]
