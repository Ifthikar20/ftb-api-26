from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Capture the Plan choices change to the new 3-tier model:
    Individual ($45/mo) is now first-class, Pro is $100/mo,
    Enterprise renamed Business / Enterprise. Starter / Growth /
    Scale stay in the choices list as legacy aliases so existing
    Subscription rows keep validating.

    Field default flips from STARTER to INDIVIDUAL since that is now
    the canonical entry tier for new users. Existing rows with
    plan='starter' continue to resolve via the PLAN_LIMITS legacy
    mapping in core.utils.constants — no data migration required.
    """

    dependencies = [
        ("billing", "0004_alter_subscription_plan"),
    ]

    operations = [
        migrations.AlterField(
            model_name="subscription",
            name="plan",
            field=models.CharField(
                choices=[
                    ("individual", "Individual ($45/mo)"),
                    ("pro", "Pro ($100/mo)"),
                    ("enterprise", "Business / Enterprise"),
                    ("starter", "Starter (Legacy)"),
                    ("growth", "Growth (Legacy)"),
                    ("scale", "Scale (Legacy)"),
                ],
                default="individual",
                max_length=20,
            ),
        ),
    ]
