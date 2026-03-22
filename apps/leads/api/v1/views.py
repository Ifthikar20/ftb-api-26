from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from apps.leads.models import LeadSegment, ScoringConfig, EmailCampaign
from apps.leads.services.lead_service import LeadService
from apps.leads.api.v1.serializers import (
    LeadSerializer,
    LeadNoteSerializer,
    LeadSegmentSerializer,
    ScoringConfigSerializer,
    EmailCampaignSerializer,
    CampaignRecipientSerializer,
)
from apps.websites.services.website_service import WebsiteService
from core.interceptors.pagination import StandardPagination
from core.exceptions import ResourceNotFound


class LeadListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        min_score = request.query_params.get("min_score")
        lead_status = request.query_params.get("status")
        leads = LeadService.get_leads(
            website_id=website_id,
            status=lead_status,
            min_score=int(min_score) if min_score else None,
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(leads, request)
        serializer = LeadSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class HotLeadsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        leads = LeadService.get_leads(website_id=website_id, min_score=70)
        paginator = StandardPagination()
        page = paginator.paginate_queryset(leads, request)
        serializer = LeadSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class LeadDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id, lead_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        lead = LeadService.get_lead(website_id=website_id, lead_id=lead_id)
        return Response(LeadSerializer(lead).data)

    def put(self, request, website_id, lead_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        lead = LeadService.get_lead(website_id=website_id, lead_id=lead_id)
        new_status = request.data.get("status")
        if new_status:
            lead = LeadService.update_status(lead=lead, status=new_status, user=request.user)
        return Response(LeadSerializer(lead).data)


class LeadNoteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, website_id, lead_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        lead = LeadService.get_lead(website_id=website_id, lead_id=lead_id)
        content = request.data.get("content", "")
        note = LeadService.add_note(lead=lead, content=content, user=request.user)
        return Response(LeadNoteSerializer(note).data, status=status.HTTP_201_CREATED)


class LeadExportView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        csv_data = LeadService.export_csv(website_id=website_id)
        response = HttpResponse(csv_data, content_type="text/csv")
        response["Content-Disposition"] = f"attachment; filename=leads-{website_id}.csv"
        return response


class AILeadFinderView(APIView):
    """AI-powered lead discovery — search LinkedIn & Twitter via natural language."""
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        """Return current lead finder configuration status."""
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        from apps.leads.services.ai_lead_finder import google_search_configured
        from django.conf import settings

        return Response({
            "google_search_configured": google_search_configured(),
            "ai_model_configured": bool(getattr(settings, "ANTHROPIC_API_KEY", "")),
            "search_engines": ["linkedin", "twitter"],
            "fallback_available": bool(getattr(settings, "ANTHROPIC_API_KEY", "")),
        })

    def post(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        prompt = request.data.get("prompt", "").strip()
        if not prompt:
            return Response(
                {"error": "A search prompt is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from apps.leads.services.ai_lead_finder import AILeadFinder

        result = AILeadFinder.search(prompt)
        return Response(result)


class ScoringConfigView(APIView):
    """Get or update per-website lead scoring configuration."""
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)
        config, _ = ScoringConfig.objects.get_or_create(
            website=website, defaults={"threshold": 70, "weights": {}}
        )
        return Response(ScoringConfigSerializer(config).data)

    def put(self, request, website_id):
        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)
        config, _ = ScoringConfig.objects.get_or_create(
            website=website, defaults={"threshold": 70, "weights": {}}
        )
        serializer = ScoringConfigSerializer(config, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ScoringConfigSerializer(config).data)


class LeadSegmentListView(APIView):
    """List and create lead segments for a website."""
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        segments = LeadSegment.objects.filter(website_id=website_id).order_by("-created_at")
        return Response(LeadSegmentSerializer(segments, many=True).data)

    def post(self, request, website_id):
        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)
        serializer = LeadSegmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(website=website, created_by=request.user)
        return Response(LeadSegmentSerializer(serializer.instance).data, status=status.HTTP_201_CREATED)


class LeadSegmentDetailView(APIView):
    """Update or delete a single lead segment."""
    permission_classes = [IsAuthenticated]

    def _get_segment(self, user, website_id, segment_id):
        WebsiteService.get_for_user(user=user, website_id=website_id)
        try:
            return LeadSegment.objects.get(id=segment_id, website_id=website_id)
        except LeadSegment.DoesNotExist:
            raise ResourceNotFound("Segment not found.")

    def put(self, request, website_id, segment_id):
        segment = self._get_segment(request.user, website_id, segment_id)
        serializer = LeadSegmentSerializer(segment, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(LeadSegmentSerializer(segment).data)

    def delete(self, request, website_id, segment_id):
        segment = self._get_segment(request.user, website_id, segment_id)
        segment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class LeadEmailView(APIView):
    """Send emails to leads and view email history."""
    permission_classes = [IsAuthenticated]

    def post(self, request, website_id, lead_id):
        """Send an email to a lead."""
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        subject = request.data.get("subject", "").strip()
        body = request.data.get("body", "").strip()
        if not subject or not body:
            return Response(
                {"error": "Subject and body are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from apps.leads.services.email_service import LeadEmailService

        try:
            email_record = LeadEmailService.send_email(
                lead_id=lead_id, subject=subject, body=body, sent_by=request.user
            )
            return Response({
                "success": True,
                "status": email_record.status,
                "email_id": email_record.id,
            }, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, website_id, lead_id):
        """Get email history for a lead."""
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        from apps.leads.services.email_service import LeadEmailService

        emails = LeadEmailService.get_email_history(lead_id=lead_id)
        return Response(emails)


# ── Email Campaigns ──────────────────────────────────────────────────────────

class CampaignListView(APIView):
    """List and create email campaigns for a website."""
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        from apps.leads.services.campaign_service import CampaignService

        campaigns = CampaignService.list(website_id=website_id)
        paginator = StandardPagination()
        page = paginator.paginate_queryset(campaigns, request)
        return paginator.get_paginated_response(EmailCampaignSerializer(page, many=True).data)

    def post(self, request, website_id):
        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)
        serializer = EmailCampaignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        from apps.leads.services.campaign_service import CampaignService

        campaign = CampaignService.create(
            website=website,
            created_by=request.user,
            subject=serializer.validated_data["subject"],
            body=serializer.validated_data["body"],
            segment=serializer.validated_data.get("segment"),
            canva_design_url=serializer.validated_data.get("canva_design_url", ""),
        )
        return Response(EmailCampaignSerializer(campaign).data, status=status.HTTP_201_CREATED)


class CampaignDetailView(APIView):
    """Retrieve, update, or delete a campaign."""
    permission_classes = [IsAuthenticated]

    def _get_campaign(self, user, website_id, campaign_id):
        WebsiteService.get_for_user(user=user, website_id=website_id)
        from apps.leads.services.campaign_service import CampaignService
        return CampaignService.get(website_id=website_id, campaign_id=campaign_id)

    def get(self, request, website_id, campaign_id):
        campaign = self._get_campaign(request.user, website_id, campaign_id)
        return Response(EmailCampaignSerializer(campaign).data)

    def put(self, request, website_id, campaign_id):
        campaign = self._get_campaign(request.user, website_id, campaign_id)
        if campaign.status not in (EmailCampaign.STATUS_DRAFT, EmailCampaign.STATUS_FAILED):
            return Response(
                {"error": "Only draft or failed campaigns can be edited."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = EmailCampaignSerializer(campaign, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(EmailCampaignSerializer(campaign).data)

    def delete(self, request, website_id, campaign_id):
        campaign = self._get_campaign(request.user, website_id, campaign_id)
        if campaign.status == EmailCampaign.STATUS_SENDING:
            return Response(
                {"error": "Cannot delete a campaign that is currently sending."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        campaign.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CampaignSendView(APIView):
    """Trigger sending a campaign."""
    permission_classes = [IsAuthenticated]

    def post(self, request, website_id, campaign_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        from apps.leads.services.campaign_service import CampaignService

        campaign = CampaignService.get(website_id=website_id, campaign_id=campaign_id)
        try:
            campaign = CampaignService.send(campaign=campaign, sent_by=request.user)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(EmailCampaignSerializer(campaign).data)


class CampaignStatsView(APIView):
    """Get detailed stats for a sent campaign."""
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id, campaign_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        from apps.leads.services.campaign_service import CampaignService

        campaign = CampaignService.get(website_id=website_id, campaign_id=campaign_id)
        stats = CampaignService.get_stats(campaign=campaign)

        # Pull live Mailchimp stats if available
        if campaign.mailchimp_campaign_id:
            try:
                from apps.websites.models import Integration
                from apps.leads.services.mailchimp_service import MailchimpService

                integration = Integration.objects.get(
                    website_id=website_id, type="mailchimp", is_active=True
                )
                mc_stats = MailchimpService.get_campaign_report(
                    integration=integration,
                    mailchimp_campaign_id=campaign.mailchimp_campaign_id,
                )
                stats["mailchimp"] = mc_stats
            except Exception:
                pass

        return Response(stats)


class CampaignRecipientsView(APIView):
    """List recipients for a campaign."""
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id, campaign_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        from apps.leads.services.campaign_service import CampaignService
        from apps.leads.models import CampaignRecipient

        campaign = CampaignService.get(website_id=website_id, campaign_id=campaign_id)
        recipients = CampaignRecipient.objects.filter(campaign=campaign).select_related("lead")
        paginator = StandardPagination()
        page = paginator.paginate_queryset(recipients, request)
        return paginator.get_paginated_response(CampaignRecipientSerializer(page, many=True).data)


# ── Tracked Links ─────────────────────────────────────────────────────────────

class TrackedLinkListView(APIView):
    """Create and list tracked links for a website."""
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        from apps.analytics.models import TrackedLink

        links = TrackedLink.objects.filter(website_id=website_id).order_by("-created_at")
        paginator = StandardPagination()
        page = paginator.paginate_queryset(links, request)
        return paginator.get_paginated_response(_serialize_tracked_links(page))

    def post(self, request, website_id):
        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)
        destination_url = request.data.get("destination_url", "").strip()
        if not destination_url:
            return Response({"error": "destination_url is required."}, status=status.HTTP_400_BAD_REQUEST)

        from apps.analytics.services.tracking_service import TrackingService
        from apps.leads.models import EmailCampaign

        campaign = None
        campaign_id = request.data.get("campaign_id")
        if campaign_id:
            try:
                campaign = EmailCampaign.objects.get(id=campaign_id, website=website)
            except EmailCampaign.DoesNotExist:
                pass

        link = TrackingService.create_link(
            website=website,
            destination_url=destination_url,
            description=request.data.get("description", ""),
            campaign=campaign,
        )
        return Response(_serialize_tracked_link(link), status=status.HTTP_201_CREATED)


class TrackedLinkDetailView(APIView):
    """Retrieve or delete a tracked link."""
    permission_classes = [IsAuthenticated]

    def _get_link(self, user, website_id, link_id):
        WebsiteService.get_for_user(user=user, website_id=website_id)
        from apps.analytics.models import TrackedLink
        try:
            return TrackedLink.objects.get(id=link_id, website_id=website_id)
        except TrackedLink.DoesNotExist:
            raise ResourceNotFound("Tracked link not found.")

    def get(self, request, website_id, link_id):
        link = self._get_link(request.user, website_id, link_id)
        from apps.analytics.services.tracking_service import TrackingService
        data = _serialize_tracked_link(link)
        data["stats"] = TrackingService.get_click_stats(tracked_link=link)
        return Response(data)

    def delete(self, request, website_id, link_id):
        link = self._get_link(request.user, website_id, link_id)
        link.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TrackedLinkClicksView(APIView):
    """List clicks for a tracked link."""
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id, link_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        from apps.analytics.models import TrackedLink, LinkClick
        try:
            link = TrackedLink.objects.get(id=link_id, website_id=website_id)
        except TrackedLink.DoesNotExist:
            raise ResourceNotFound("Tracked link not found.")

        clicks = LinkClick.objects.filter(tracked_link=link).order_by("-clicked_at")
        paginator = StandardPagination()
        page = paginator.paginate_queryset(clicks, request)
        return paginator.get_paginated_response([
            {
                "id": c.id,
                "clicked_at": c.clicked_at,
                "converted": c.converted,
                "referrer": c.referrer,
            }
            for c in page
        ])


def _serialize_tracked_link(link) -> dict:
    from django.utils import timezone
    return {
        "id": str(link.id),
        "tracking_key": link.tracking_key,
        "destination_url": link.destination_url,
        "description": link.description,
        "click_count": link.click_count,
        "conversion_count": link.conversion_count,
        "campaign_id": link.campaign_id,
        "created_at": link.created_at,
        "short_url": f"/t/{link.tracking_key}/",
    }


def _serialize_tracked_links(links) -> list:
    return [_serialize_tracked_link(l) for l in links]


# ── Connectors ────────────────────────────────────────────────────────────────

class LeadExportXlsxView(APIView):
    """Export leads as an Excel (.xlsx) file."""
    permission_classes = [IsAuthenticated]

    def post(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        xlsx_data = LeadService.export_xlsx(website_id=website_id)
        response = HttpResponse(
            xlsx_data,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f"attachment; filename=leads-{website_id}.xlsx"
        return response


class LeadExportDriveView(APIView):
    """Export leads to a Google Sheet via Google Drive."""
    permission_classes = [IsAuthenticated]

    def post(self, request, website_id):
        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)
        from apps.websites.models import Integration
        from apps.leads.services.drive_service import DriveService

        try:
            integration = Integration.objects.get(
                website=website, type="google_drive", is_active=True
            )
        except Integration.DoesNotExist:
            return Response(
                {"error": "Google Drive is not connected. Connect it under Integrations."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = DriveService.export_leads_to_sheet(
                website_id=str(website_id),
                integration=integration,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response(result)
