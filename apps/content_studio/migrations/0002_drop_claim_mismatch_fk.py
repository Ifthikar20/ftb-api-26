"""Drop the ContentBrief -> claim_verifier.ClaimMismatch FK column.

The Accuracy product (claim_verifier app + Accuracy frontend page) has
been retired. ContentBrief used to point at a ClaimMismatch when the
brief was generated from a high-severity claim contradiction; that
code path is gone and the column is unused.

We also edited 0001_initial.py to remove the original field
declaration so fresh databases never see this column at all. This
migration only matters for databases that already applied 0001 with
the column in place — on those, drop it. On fresh databases the
``IF EXISTS`` clause makes the statement a no-op.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("content_studio", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "ALTER TABLE content_studio_contentbrief "
                "DROP COLUMN IF EXISTS target_claim_mismatch_id;"
            ),
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
