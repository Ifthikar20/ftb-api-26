"""
Google Drive export service — exports leads as a Google Sheet via the Drive/Sheets API.

Requires:
  - GOOGLE_OAUTH_CLIENT_ID / GOOGLE_OAUTH_CLIENT_SECRET in settings
  - An Integration record of type "google_drive" with a valid access_token for the user
  - google-api-python-client, google-auth packages installed
"""
import logging

logger = logging.getLogger("apps")


class DriveService:
    @staticmethod
    def _sheets_service(access_token: str):
        """Build an authenticated Sheets API service client."""
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            creds = Credentials(token=access_token)
            return build("sheets", "v4", credentials=creds, cache_discovery=False)
        except ImportError:
            raise RuntimeError(
                "google-api-python-client is not installed. "
                "Run: pip install google-api-python-client google-auth"
            )

    @staticmethod
    def export_leads_to_sheet(*, website_id: str, integration) -> dict:
        """
        Export all leads for a website to a new Google Sheet.

        Returns a dict with the spreadsheet URL and ID.
        """
        from apps.leads.models import Lead

        leads = Lead.objects.filter(website_id=website_id).select_related("visitor").order_by("-score")
        access_token = integration.access_token

        service = DriveService._sheets_service(access_token)

        # Build sheet data
        headers = ["ID", "Score", "Status", "Email", "Name", "Company", "Source", "Country", "Created At"]
        rows = [headers]
        for lead in leads:
            rows.append([
                str(lead.id),
                lead.score,
                lead.status,
                lead.email,
                lead.name,
                lead.company,
                lead.source,
                lead.visitor.geo_country if lead.visitor else "",
                lead.created_at.isoformat(),
            ])

        # Create spreadsheet
        spreadsheet_body = {
            "properties": {"title": f"Leads Export — {website_id}"},
            "sheets": [{"properties": {"title": "Leads"}}],
        }
        spreadsheet = service.spreadsheets().create(body=spreadsheet_body).execute()
        spreadsheet_id = spreadsheet["spreadsheetId"]
        sheet_url = spreadsheet["spreadsheetUrl"]

        # Write data
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range="Leads!A1",
            valueInputOption="RAW",
            body={"values": rows},
        ).execute()

        logger.info(
            "Exported %d leads for website %s to Google Sheet %s",
            len(rows) - 1,
            website_id,
            spreadsheet_id,
        )
        return {
            "spreadsheet_id": spreadsheet_id,
            "spreadsheet_url": sheet_url,
            "lead_count": len(rows) - 1,
        }
