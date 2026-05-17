"""
Stub models for the retired `leads` app.

The app and its tables were removed (see apps/accounts/migrations/
0012_drop_leads_keyword_tables.py), but historical migrations in
`analytics` still reference `leads.EmailCampaign` and
`leads.CampaignRecipient` via ForeignKey. Removing the FK columns
happens in apps/analytics/migrations/0008_drop_campaign_fks.py, but
Django still validates the lazy references when building the
migration graph, so the `leads` app must remain importable.

These models are `managed = False`: Django will not create or alter
their tables. The actual DB tables are gone.
"""
from django.db import models


class EmailCampaign(models.Model):
    id = models.BigAutoField(primary_key=True)

    class Meta:
        managed = False
        db_table = "leads_emailcampaign"


class CampaignRecipient(models.Model):
    id = models.BigAutoField(primary_key=True)

    class Meta:
        managed = False
        db_table = "leads_campaignrecipient"
