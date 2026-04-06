import logging

from apps.social_leads.models import SocialLead, SocialLeadSource

logger = logging.getLogger("apps")


class LeadProcessor:
    """
    Converts a SocialLead into a FetchBot Lead record and optionally queues
    an outbound voice agent call.
    """

    @staticmethod
    def process(social_lead: SocialLead) -> None:
        """Create a Lead from this social lead and mark it processed."""
        if social_lead.is_processed:
            return

        try:
            from apps.leads.models import Lead

            name = social_lead.full_name
            lead, created = Lead.objects.get_or_create(
                website=social_lead.website,
                email=social_lead.email or None,
                defaults={
                    "name": name,
                    "company": social_lead.company,
                    "source": f"social:{social_lead.source.platform}",
                    "score": 50,
                },
            )
            if created:
                logger.info(
                    "social_lead.lead_created",
                    extra={"social_lead_id": str(social_lead.id), "lead_id": str(lead.id)},
                )

            social_lead.lead = lead
            social_lead.is_processed = True
            social_lead.save(update_fields=["lead", "is_processed", "updated_at"])

            SocialLeadSource.objects.filter(id=social_lead.source_id).update(
                total_leads_imported=SocialLeadSource.objects.filter(
                    id=social_lead.source_id
                ).values_list("total_leads_imported", flat=True)[0] + 1
            )

        except Exception as exc:
            logger.exception(
                "social_lead.process_failed",
                extra={"social_lead_id": str(social_lead.id), "error": str(exc)},
            )


class FacebookLeadService:
    """
    Handles incoming leads from Facebook Lead Ads via the Meta Webhooks API.

    Setup:
    1. Create a Meta App at developers.facebook.com
    2. Add the Webhooks product and subscribe to 'leadgen' events
    3. Set the webhook URL to /api/v1/social-leads/webhook/facebook/
    4. Use the verify_token stored in SocialLeadSource.webhook_verify_token
    5. When a lead arrives, this service fetches the full lead data via Graph API
    """

    GRAPH_BASE = "https://graph.facebook.com/v18.0"

    @classmethod
    def handle_webhook(cls, payload: dict) -> int:
        """
        Process a Facebook webhook payload. Returns count of leads created.
        """
        created = 0
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                if change.get("field") != "leadgen":
                    continue
                value = change.get("value", {})
                lead_id = value.get("leadgen_id")
                form_id = value.get("form_id")
                page_id = value.get("page_id")

                source = SocialLeadSource.objects.filter(
                    platform=SocialLeadSource.PLATFORM_FACEBOOK,
                    form_id=form_id,
                    is_active=True,
                ).first()

                if not source:
                    logger.warning(
                        "facebook.webhook.no_source",
                        extra={"form_id": form_id, "page_id": page_id},
                    )
                    continue

                # Skip duplicate
                if SocialLead.objects.filter(
                    source=source, external_lead_id=lead_id
                ).exists():
                    continue

                lead_data = cls._fetch_lead(lead_id, source.access_token)
                if not lead_data:
                    continue

                field_data = {
                    f["name"]: f["values"][0]
                    for f in lead_data.get("field_data", [])
                    if f.get("values")
                }

                social_lead = SocialLead.objects.create(
                    source=source,
                    website=source.website,
                    external_lead_id=lead_id,
                    first_name=field_data.get("first_name", ""),
                    last_name=field_data.get("last_name", ""),
                    email=field_data.get("email", ""),
                    phone=field_data.get("phone_number", ""),
                    company=field_data.get("company_name", ""),
                    job_title=field_data.get("job_title", ""),
                    form_data=field_data,
                )
                LeadProcessor.process(social_lead)
                created += 1

        return created

    @classmethod
    def _fetch_lead(cls, lead_id: str, access_token: str) -> dict:
        """Fetch full lead data from Facebook Graph API."""
        try:
            import urllib.request
            import json

            url = f"{cls.GRAPH_BASE}/{lead_id}?fields=field_data,created_time&access_token={access_token}"
            with urllib.request.urlopen(url, timeout=10) as resp:
                return json.loads(resp.read())
        except Exception as exc:
            logger.exception(
                "facebook.lead_fetch_failed",
                extra={"lead_id": lead_id, "error": str(exc)},
            )
            return {}


class LinkedInLeadService:
    """
    Handles leads from LinkedIn Lead Gen Forms via polling.

    LinkedIn does not support real-time webhooks for lead gen forms.
    This service polls the LinkedIn Marketing API every 15 minutes via a Celery beat task.

    Setup:
    1. Create a LinkedIn App at developer.linkedin.com
    2. Add the 'Lead Sync API' permission
    3. Complete OAuth flow and store access_token in SocialLeadSource
    4. Create a SocialLeadSource with platform='linkedin' and form_id=<form_id>
    """

    API_BASE = "https://api.linkedin.com/v2"

    @classmethod
    def sync_source(cls, source: SocialLeadSource) -> int:
        """Poll LinkedIn for new leads since last sync. Returns count imported."""
        created = 0
        try:
            responses = cls._fetch_responses(source)
            for response in responses:
                lead_id = response.get("id", "")
                if SocialLead.objects.filter(
                    source=source, external_lead_id=str(lead_id)
                ).exists():
                    continue

                fields = {
                    item.get("questionId", ""): item.get("answerDetails", {}).get("textAnswer", "")
                    for item in response.get("submittedAt", {}).get("questionAnswers", [])
                }

                person = response.get("person", {})
                first = person.get("firstName", {}).get("localized", {})
                last = person.get("lastName", {}).get("localized", {})
                first_name = next(iter(first.values()), "") if first else ""
                last_name = next(iter(last.values()), "") if last else ""

                social_lead = SocialLead.objects.create(
                    source=source,
                    website=source.website,
                    external_lead_id=str(lead_id),
                    first_name=first_name,
                    last_name=last_name,
                    email=fields.get("email", ""),
                    phone=fields.get("phone", ""),
                    company=fields.get("company", ""),
                    job_title=fields.get("jobTitle", ""),
                    linkedin_profile=person.get("publicProfileUrl", ""),
                    form_data=response,
                )
                LeadProcessor.process(social_lead)
                created += 1

            from django.utils import timezone
            source.last_synced_at = timezone.now()
            source.save(update_fields=["last_synced_at", "updated_at"])

        except Exception as exc:
            logger.exception(
                "linkedin.sync_failed",
                extra={"source_id": str(source.id), "error": str(exc)},
            )
        return created

    @classmethod
    def _fetch_responses(cls, source: SocialLeadSource) -> list:
        """Fetch lead gen form responses from LinkedIn API."""
        try:
            import urllib.request
            import urllib.parse
            import json

            params = urllib.parse.urlencode({
                "q": "owner",
                "owner": f"urn:li:organization:{source.account_id}",
                "formUrn": f"urn:li:leadGenForm:{source.form_id}",
                "count": 100,
            })
            url = f"{cls.API_BASE}/leadGenFormResponses?{params}"
            req = urllib.request.Request(
                url,
                headers={"Authorization": f"Bearer {source.access_token}"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
                return data.get("elements", [])
        except Exception as exc:
            logger.exception(
                "linkedin.fetch_failed",
                extra={"source_id": str(source.id), "error": str(exc)},
            )
            return []


class XLeadService:
    """
    X (Twitter) does not provide a native lead generation form product.

    Supported methods:
    1. Pixel tracking: FetchBot tracking pixel captures visitors referred by X campaigns.
    2. CSV import: Export from X Ads Manager and import via the Leads > Import CSV feature.
    3. X Ads API: Retrieve engagement data for users who clicked on promoted posts
       (requires X Ads API access, applied separately at ads.twitter.com/developer).
    """

    @staticmethod
    def import_csv(website, csv_rows: list) -> int:
        """
        Import leads from a CSV export from X Ads Manager.
        Expected columns: name, email, phone (any order, case-insensitive headers).
        """
        from apps.leads.models import Lead

        source, _ = SocialLeadSource.objects.get_or_create(
            website=website,
            platform=SocialLeadSource.PLATFORM_X,
            form_id="csv_import",
            defaults={"label": "X CSV Import", "is_active": True},
        )

        created = 0
        for row in csv_rows:
            row_lower = {k.lower().strip(): v for k, v in row.items()}
            email = row_lower.get("email", "").strip()
            name = row_lower.get("name", "").strip() or row_lower.get("full_name", "").strip()
            phone = row_lower.get("phone", "").strip()

            if not email and not phone:
                continue

            social_lead = SocialLead.objects.create(
                source=source,
                website=website,
                first_name=name.split(" ")[0] if name else "",
                last_name=" ".join(name.split(" ")[1:]) if " " in name else "",
                email=email,
                phone=phone,
                form_data=row,
            )
            LeadProcessor.process(social_lead)
            created += 1

        return created
