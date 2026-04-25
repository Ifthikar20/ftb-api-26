import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("websites", "0004_website_onboarding_completed_platform_type"),
        ("leads", "0002_emailcampaign_campaignrecipient"),
    ]

    operations = [
        migrations.CreateModel(
            name="SocialLeadSource",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("platform", models.CharField(
                    choices=[
                        ("facebook", "Facebook Lead Ads"),
                        ("instagram", "Instagram (via Facebook)"),
                        ("linkedin", "LinkedIn Lead Gen Forms"),
                        ("tiktok", "TikTok Lead Generation"),
                        ("x", "X (Twitter)"),
                        ("google", "Google Lead Form Extensions"),
                    ],
                    max_length=20,
                )),
                ("label", models.CharField(blank=True, max_length=200)),
                ("is_active", models.BooleanField(default=True)),
                ("account_id", models.CharField(blank=True, max_length=200)),
                ("form_id", models.CharField(blank=True, max_length=200)),
                ("campaign_name", models.CharField(blank=True, max_length=300)),
                ("access_token", models.TextField(blank=True)),
                ("refresh_token", models.TextField(blank=True)),
                ("token_expires_at", models.DateTimeField(blank=True, null=True)),
                ("webhook_verify_token", models.CharField(blank=True, max_length=200)),
                ("total_leads_imported", models.IntegerField(default=0)),
                ("last_synced_at", models.DateTimeField(blank=True, null=True)),
                ("website", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="social_lead_sources",
                    to="websites.website",
                )),
            ],
            options={"db_table": "social_leads_source", "ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="socialleadsource",
            constraint=models.UniqueConstraint(
                fields=["website", "platform", "form_id"],
                name="unique_website_platform_form",
            ),
        ),
        migrations.CreateModel(
            name="SocialLead",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("external_lead_id", models.CharField(blank=True, db_index=True, max_length=300)),
                ("first_name", models.CharField(blank=True, max_length=200)),
                ("last_name", models.CharField(blank=True, max_length=200)),
                ("email", models.EmailField(blank=True, db_index=True)),
                ("phone", models.CharField(blank=True, max_length=30)),
                ("company", models.CharField(blank=True, max_length=200)),
                ("job_title", models.CharField(blank=True, max_length=200)),
                ("linkedin_profile", models.URLField(blank=True)),
                ("form_data", models.JSONField(default=dict)),
                ("is_processed", models.BooleanField(default=False)),
                ("source", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="leads",
                    to="social_leads.socialleadsource",
                )),
                ("website", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="social_leads",
                    to="websites.website",
                )),
                ("lead", models.OneToOneField(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="social_lead",
                    to="leads.lead",
                )),
            ],
            options={"db_table": "social_leads_lead", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="sociallead",
            index=models.Index(fields=["website", "is_processed"], name="soc_lead_website_processed_idx"),
        ),
        migrations.AddIndex(
            model_name="sociallead",
            index=models.Index(fields=["source", "external_lead_id"], name="soc_lead_source_ext_idx"),
        ),
    ]
