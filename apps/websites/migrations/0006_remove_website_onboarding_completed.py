from django.db import migrations


class Migration(migrations.Migration):
    """
    Drop the obsolete `onboarding_completed` field from Website. The
    per-website onboarding flow has been consolidated into the
    account-level /app-onboarding page.
    """

    dependencies = [
        ("websites", "0005_add_description_and_topics"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="website",
            name="onboarding_completed",
        ),
    ]
