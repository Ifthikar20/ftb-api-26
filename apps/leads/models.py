"""The retired `leads` app.

The app's features were removed long ago (see
apps/accounts/migrations/0012_drop_leads_keyword_tables.py and
apps/analytics/migrations/0008_drop_campaign_fks.py). Two stub models
survived here as `managed = False` placeholders so Django could still
resolve the lazy `leads.EmailCampaign` / `leads.CampaignRecipient`
references in those historical migrations.

Because they were unmanaged, Django never dropped their tables --
`leads_emailcampaign` and `leads_campaignrecipient` were still sitting
in the database, empty, until migration 0002 removed them with explicit
SQL. The stubs are gone with them; the historical migrations that name
them are already past the point where the reference is resolved.

The app stays in INSTALLED_APPS so its own migration history remains
applicable. It intentionally defines no models.
"""
