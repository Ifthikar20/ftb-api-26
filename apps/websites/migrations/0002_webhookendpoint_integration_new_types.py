from django.db import migrations, models
import django.db.models.deletion
import core.encryption.field_encryption


class Migration(migrations.Migration):

    dependencies = [
        ("websites", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="WebhookEndpoint",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("url", models.URLField(max_length=500)),
                ("events", models.JSONField(default=list)),
                ("secret", core.encryption.field_encryption.EncryptedTextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("last_triggered_at", models.DateTimeField(blank=True, null=True)),
                ("failure_count", models.IntegerField(default=0)),
                (
                    "website",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="webhook_endpoints",
                        to="websites.website",
                    ),
                ),
            ],
            options={"db_table": "websites_webhookendpoint"},
        ),
        migrations.AlterField(
            model_name="integration",
            name="type",
            field=models.CharField(
                choices=[
                    ("ga", "Google Analytics"),
                    ("gsc", "Google Search Console"),
                    ("facebook", "Facebook Ads"),
                    ("shopify", "Shopify"),
                    ("mailchimp", "Mailchimp"),
                    ("google_drive", "Google Drive"),
                    ("canva", "Canva"),
                    ("hubspot", "HubSpot"),
                ],
                max_length=20,
            ),
        ),
    ]
