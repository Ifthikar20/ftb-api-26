import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("voice_agent", "0003_outbound_campaigns"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("websites", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="agentconfig",
            name="is_active",
            field=models.BooleanField(
                default=True,
                help_text=(
                    "Always-on. Retained for backward compatibility; "
                    "agent is enabled by default."
                ),
            ),
        ),
        migrations.AddField(
            model_name="phonenumber",
            name="is_verified",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "True once the user has completed SMS/call MFA "
                    "proving ownership of this number."
                ),
            ),
        ),
        migrations.AddField(
            model_name="phonenumber",
            name="verified_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="PhoneVerification",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("number", models.CharField(help_text="E.164 number being verified", max_length=30)),
                ("channel", models.CharField(
                    choices=[("sms", "SMS"), ("call", "Voice call")],
                    default="sms",
                    max_length=10,
                )),
                ("code_hash", models.CharField(help_text="HMAC-SHA256 of the OTP", max_length=128)),
                ("expires_at", models.DateTimeField()),
                ("attempts", models.PositiveIntegerField(default=0)),
                ("max_attempts", models.PositiveIntegerField(default=5)),
                ("status", models.CharField(
                    choices=[
                        ("pending", "Pending"),
                        ("verified", "Verified"),
                        ("expired", "Expired"),
                        ("failed", "Failed"),
                    ],
                    default="pending",
                    max_length=12,
                )),
                ("vendor_request_id", models.CharField(
                    blank=True,
                    help_text="Vendor (Telnyx/Twilio) message or call SID for tracing.",
                    max_length=200,
                )),
                ("requested_by", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to=settings.AUTH_USER_MODEL,
                )),
                ("website", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="phone_verifications",
                    to="websites.website",
                )),
            ],
            options={
                "db_table": "voice_agent_phoneverification",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["website", "number", "status"], name="va_phv_web_num_status_idx"),
                ],
            },
        ),
    ]
