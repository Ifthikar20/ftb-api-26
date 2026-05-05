from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Sync ``User.plan`` and ``Organization.plan`` choices with the new
    3-tier model (Individual / Pro / Business). Starter / Growth /
    Scale stay in the choices as legacy aliases so existing rows keep
    validating.

    User default flips from STARTER to INDIVIDUAL since that's now the
    canonical entry tier. Organization default keeps Enterprise — orgs
    are pre-paid only.
    """

    THREE_TIER_CHOICES = [
        ("individual", "Individual ($45/mo)"),
        ("pro", "Pro ($100/mo)"),
        ("enterprise", "Business / Enterprise"),
        ("starter", "Starter (Legacy)"),
        ("growth", "Growth (Legacy)"),
        ("scale", "Scale (Legacy)"),
    ]

    dependencies = [
        ("accounts", "0007_user_cost_cap_perplexity_provider"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="plan",
            field=models.CharField(
                choices=THREE_TIER_CHOICES,
                default="individual",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="organization",
            name="plan",
            field=models.CharField(
                choices=THREE_TIER_CHOICES,
                default="enterprise",
                max_length=20,
            ),
        ),
    ]
