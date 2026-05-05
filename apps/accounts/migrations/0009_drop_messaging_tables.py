from django.db import migrations


# One-shot cleanup. The apps.messaging module was deleted from the
# codebase when the product narrowed focus to LLM ranking + GEO. The
# tables it created stay in the dev / staging / prod database as
# orphans until they're dropped — which is what this migration does.
#
# Hosted in the ``accounts`` app because (a) accounts is always loaded
# so this migration always runs, and (b) we don't want to recreate a
# stub messaging app just to host a deletion migration.
#
# All ``DROP TABLE IF EXISTS`` so re-running on a database that's
# already had the tables dropped is a no-op. ``CASCADE`` releases the
# FKs leads/social_leads might have held — there are none in the
# current codebase, but the cascade is cheap insurance.
DROP_SQL = """
DROP TABLE IF EXISTS messaging_message            CASCADE;
DROP TABLE IF EXISTS messaging_conversation       CASCADE;
DROP TABLE IF EXISTS messaging_contact            CASCADE;
DROP TABLE IF EXISTS messaging_channel            CASCADE;
DROP TABLE IF EXISTS messaging_agenttrainingdoc   CASCADE;
DROP TABLE IF EXISTS messaging_aiinstruction      CASCADE;
"""

# Reverse is intentionally a no-op. We're not going to recreate the
# six tables on rollback — if you need messaging back, restore the
# app code from git history and re-apply its migrations.
NOOP_SQL = "SELECT 1;"


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0008_alter_plan_three_tier"),
    ]

    operations = [
        migrations.RunSQL(sql=DROP_SQL, reverse_sql=NOOP_SQL),
    ]
