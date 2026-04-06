import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("voice_agent", "0001_initial"),
        ("websites", "0004_website_onboarding_completed_platform_type"),
    ]

    operations = [
        migrations.CreateModel(
            name="PhoneNumber",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("number", models.CharField(help_text="E.164 format, e.g. +12025551234", max_length=30)),
                ("label", models.CharField(blank=True, help_text="Human-readable label, e.g. 'Main Line', 'Sales Line'", max_length=100)),
                ("provider", models.CharField(
                    choices=[("telnyx", "Telnyx"), ("twilio", "Twilio"), ("retell", "Retell AI"), ("other", "Other")],
                    default="telnyx",
                    max_length=20,
                )),
                ("is_active", models.BooleanField(default=True)),
                ("forwarded_to_agent", models.BooleanField(
                    default=True,
                    help_text="Route inbound calls from this number to the AI voice agent.",
                )),
                ("website", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="phone_numbers",
                    to="websites.website",
                )),
            ],
            options={
                "db_table": "voice_agent_phonenumber",
                "ordering": ["created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="phonenumber",
            constraint=models.UniqueConstraint(fields=["website", "number"], name="unique_website_number"),
        ),
        migrations.CreateModel(
            name="AgentContextDocument",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("title", models.CharField(help_text="e.g. 'Services & Pricing', 'FAQs'", max_length=200)),
                ("content", models.TextField(help_text="Markdown content injected into the AI system prompt.")),
                ("is_active", models.BooleanField(default=True, help_text="Only active documents are included in calls.")),
                ("sort_order", models.IntegerField(default=0, help_text="Lower values appear first in the prompt.")),
                ("website", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="agent_context_docs",
                    to="websites.website",
                )),
            ],
            options={
                "db_table": "voice_agent_contextdocument",
                "ordering": ["sort_order", "created_at"],
            },
        ),
    ]
