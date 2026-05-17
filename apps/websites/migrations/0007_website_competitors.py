from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("websites", "0006_remove_website_onboarding_completed"),
    ]

    operations = [
        migrations.AddField(
            model_name="website",
            name="competitors",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Selected competitor brands as [{name, domain}]",
            ),
        ),
    ]
