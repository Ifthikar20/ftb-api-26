"""Capture structured dismissal metadata on ClaimMismatch."""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("claim_verifier", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="claimmismatch",
            name="dismissal_reason",
            field=models.CharField(
                blank=True, max_length=32,
                choices=[
                    ("false_positive", "False positive"),
                    ("not_about_us", "Not about our brand"),
                    ("vault_outdated", "Our vault is outdated"),
                    ("low_severity", "Acceptable inaccuracy"),
                    ("other", "Other"),
                ],
            ),
        ),
        migrations.AddField(
            model_name="claimmismatch",
            name="dismissal_note",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="claimmismatch",
            name="dismissed_by",
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
