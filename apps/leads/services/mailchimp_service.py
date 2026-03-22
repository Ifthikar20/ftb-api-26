"""
Mailchimp integration service.

Uses the Mailchimp Marketing API v3 via the mailchimp-marketing Python client.
Credentials are stored in the Integration model (access_token = API key, metadata["list_id"]).
"""
import logging

logger = logging.getLogger("apps")


class MailchimpService:
    @staticmethod
    def _client(api_key: str, server_prefix: str):
        """Return an authenticated Mailchimp client."""
        try:
            import mailchimp_marketing as MailchimpMarketing
            client = MailchimpMarketing.Client()
            client.set_config({"api_key": api_key, "server": server_prefix})
            return client
        except ImportError:
            raise RuntimeError(
                "mailchimp-marketing package is not installed. "
                "Run: pip install mailchimp-marketing"
            )

    @staticmethod
    def _parse_credentials(integration):
        """Extract API key and server prefix from Integration record."""
        api_key = integration.access_token
        # Server prefix is stored as metadata["server_prefix"] e.g. "us1"
        server_prefix = integration.metadata.get("server_prefix", "us1")
        list_id = integration.metadata.get("list_id", "")
        return api_key, server_prefix, list_id

    @staticmethod
    def sync_leads_to_list(*, integration, leads) -> int:
        """Upsert leads as Mailchimp list members. Returns number synced."""
        api_key, server_prefix, list_id = MailchimpService._parse_credentials(integration)
        if not list_id:
            raise ValueError("Mailchimp list_id not configured in integration metadata.")

        client = MailchimpService._client(api_key, server_prefix)
        synced = 0

        for lead in leads:
            if not lead.email:
                continue
            try:
                client.lists.set_list_member(
                    list_id,
                    lead.email.lower(),
                    {
                        "email_address": lead.email,
                        "status_if_new": "subscribed",
                        "merge_fields": {
                            "FNAME": (lead.name or "").split()[0] if lead.name else "",
                            "LNAME": " ".join((lead.name or "").split()[1:]) if lead.name else "",
                            "COMPANY": lead.company or "",
                        },
                        "tags": [f"score:{lead.score // 10 * 10}", "fetchbot"],
                    },
                )
                synced += 1
            except Exception as e:
                logger.warning("Mailchimp sync failed for %s: %s", lead.email, e)

        return synced

    @staticmethod
    def send_campaign(*, integration, campaign, leads) -> str:
        """
        Create and send a Mailchimp campaign. Returns the Mailchimp campaign ID.

        Steps:
          1. Sync leads as list members.
          2. Create a Mailchimp campaign.
          3. Set the campaign content (HTML body).
          4. Send the campaign.
        """
        api_key, server_prefix, list_id = MailchimpService._parse_credentials(integration)
        if not list_id:
            raise ValueError("Mailchimp list_id not configured in integration metadata.")

        client = MailchimpService._client(api_key, server_prefix)

        # 1. Sync leads
        MailchimpService.sync_leads_to_list(integration=integration, leads=leads)

        # 2. Create campaign
        mc_campaign = client.campaigns.create({
            "type": "regular",
            "recipients": {"list_id": list_id},
            "settings": {
                "subject_line": campaign.subject,
                "from_name": "FetchBot",
                "reply_to": integration.metadata.get("reply_to", "noreply@growthpilot.io"),
            },
        })
        mc_campaign_id = mc_campaign["id"]

        # 3. Set content
        client.campaigns.set_content(mc_campaign_id, {"html": campaign.body})

        # 4. Send
        client.campaigns.send(mc_campaign_id)

        logger.info("Mailchimp campaign %s sent for campaign %s", mc_campaign_id, campaign.id)
        return mc_campaign_id

    @staticmethod
    def get_campaign_report(*, integration, mailchimp_campaign_id: str) -> dict:
        """Fetch open/click stats from Mailchimp for a sent campaign."""
        api_key, server_prefix, _ = MailchimpService._parse_credentials(integration)
        client = MailchimpService._client(api_key, server_prefix)

        try:
            report = client.reports.get_campaign_report(mailchimp_campaign_id)
            return {
                "emails_sent": report.get("emails_sent", 0),
                "opens": report.get("opens", {}).get("unique_opens", 0),
                "clicks": report.get("clicks", {}).get("unique_clicks", 0),
                "bounces": report.get("bounces", {}).get("hard_bounces", 0),
                "unsubscribes": report.get("unsubscribes", 0),
            }
        except Exception as e:
            logger.error("Failed to fetch Mailchimp report for %s: %s", mailchimp_campaign_id, e)
            return {}
