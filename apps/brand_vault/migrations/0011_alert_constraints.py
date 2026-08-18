"""Tighten alert identity constraints after the backfill.

Step 3 of 3: reference becomes unique and non-null, and the per-detector
uniqueness contract is enforced where a result is linked.
"""
from django.db import migrations, models

import apps.brand_vault.models


class Migration(migrations.Migration):

    dependencies = [
        ("brand_vault", "0010_alert_backfill"),
    ]

    operations = [
        migrations.AlterField(
            model_name="safetyalert",
            name="reference",
            field=models.CharField(
                default=apps.brand_vault.models.generate_alert_reference,
                editable=False,
                max_length=16,
                unique=True,
            ),
        ),
        migrations.AddIndex(
            model_name="safetyalert",
            index=models.Index(
                fields=["website", "detector_code"], name="bv_sa_w_det_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="safetyalert",
            constraint=models.UniqueConstraint(
                condition=models.Q(("result__isnull", False))
                & ~models.Q(("detector_code", "")),
                fields=("website", "result", "detector_code"),
                name="bv_sa_res_det_uniq",
            ),
        ),
    ]
