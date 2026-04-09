import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("voice_agent", "0002_phonenumber_agentcontextdocument"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="phonenumber",
            name="telnyx_trunk_id",
            field=models.CharField(
                blank=True,
                help_text="Telnyx SIP connection / trunk ID this caller-ID dials out from.",
                max_length=200,
            ),
        ),
        migrations.AddField(
            model_name="phonenumber",
            name="livekit_outbound_trunk_id",
            field=models.CharField(
                blank=True,
                help_text="LiveKit-side outbound SIP trunk ID returned from CreateSIPOutboundTrunk.",
                max_length=200,
            ),
        ),
        migrations.CreateModel(
            name="CallCampaign",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=200)),
                ("welcome_message", models.TextField(
                    help_text="Opening line played to the recipient when they answer."
                )),
                ("status", models.CharField(
                    choices=[
                        ("draft", "Draft"),
                        ("running", "Running"),
                        ("paused", "Paused"),
                        ("completed", "Completed"),
                        ("failed", "Failed"),
                    ],
                    db_index=True,
                    default="draft",
                    max_length=20,
                )),
                ("max_concurrent_calls", models.PositiveSmallIntegerField(default=3)),
                ("calls_per_minute", models.PositiveSmallIntegerField(default=10)),
                ("respect_business_hours", models.BooleanField(default=True)),
                ("created_by", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="call_campaigns",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("from_number", models.ForeignKey(
                    help_text="Caller-ID this campaign dials out from. Must belong to the same website.",
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="campaigns",
                    to="voice_agent.phonenumber",
                )),
                ("website", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="call_campaigns",
                    to="websites.website",
                )),
            ],
            options={
                "db_table": "voice_agent_callcampaign",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["website", "status"], name="va_camp_web_status_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="CallTarget",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("phone", models.CharField(db_index=True, help_text="E.164 format", max_length=30)),
                ("name", models.CharField(blank=True, max_length=200)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("status", models.CharField(
                    choices=[
                        ("pending", "Pending"),
                        ("queued", "Queued"),
                        ("dialing", "Dialing"),
                        ("in_progress", "In Progress"),
                        ("completed", "Completed"),
                        ("failed", "Failed"),
                        ("no_answer", "No Answer"),
                        ("busy", "Busy"),
                        ("do_not_call", "Do Not Call"),
                    ],
                    db_index=True,
                    default="pending",
                    max_length=20,
                )),
                ("attempt_count", models.PositiveSmallIntegerField(default=0)),
                ("max_attempts", models.PositiveSmallIntegerField(default=2)),
                ("last_attempt_at", models.DateTimeField(blank=True, null=True)),
                ("last_error", models.TextField(blank=True)),
                ("campaign", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="targets",
                    to="voice_agent.callcampaign",
                )),
            ],
            options={
                "db_table": "voice_agent_calltarget",
                "ordering": ["created_at"],
                "indexes": [
                    models.Index(fields=["campaign", "status"], name="va_target_camp_status_idx"),
                ],
                "unique_together": {("campaign", "phone")},
            },
        ),
        migrations.CreateModel(
            name="DoNotCallEntry",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("phone", models.CharField(db_index=True, max_length=30, unique=True)),
                ("reason", models.CharField(blank=True, max_length=200)),
                ("added_by", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="dnc_entries",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                "db_table": "voice_agent_donotcallentry",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddField(
            model_name="calllog",
            name="campaign",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="call_logs",
                to="voice_agent.callcampaign",
            ),
        ),
        migrations.AddField(
            model_name="calllog",
            name="target",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="call_logs",
                to="voice_agent.calltarget",
            ),
        ),
    ]
