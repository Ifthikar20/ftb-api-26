import hashlib
import hmac
import json
import logging

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.social_leads.api.v1.serializers import SocialLeadSerializer, SocialLeadSourceSerializer
from apps.social_leads.models import SocialLead, SocialLeadSource
from apps.social_leads.services.lead_processor import FacebookLeadService
from apps.websites.services.website_service import WebsiteService
from core.interceptors.pagination import StandardPagination

logger = logging.getLogger("apps")


# ── Lead Sources (per-website config) ─────────────────────────────────────────


class SocialLeadSourceListView(APIView):
    """List and create social lead source configurations."""

    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)
        sources = SocialLeadSource.objects.filter(website=website)
        return Response(SocialLeadSourceSerializer(sources, many=True).data)

    def post(self, request, website_id):
        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)
        import secrets
        serializer = SocialLeadSourceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Auto-generate a webhook verify token if not supplied
        verify_token = request.data.get("webhook_verify_token") or secrets.token_urlsafe(24)
        serializer.save(website=website, webhook_verify_token=verify_token)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class SocialLeadSourceDetailView(APIView):
    """Update or delete a social lead source."""

    permission_classes = [IsAuthenticated]

    def _get(self, request, website_id, source_id):
        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)
        return SocialLeadSource.objects.get(id=source_id, website=website)

    def put(self, request, website_id, source_id):
        source = self._get(request, website_id, source_id)
        serializer = SocialLeadSourceSerializer(source, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, website_id, source_id):
        source = self._get(request, website_id, source_id)
        source.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── Social Leads list ─────────────────────────────────────────────────────────


class SocialLeadListView(APIView):
    """List social leads for a website with optional platform filter."""

    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)
        qs = SocialLead.objects.filter(website=website).select_related("source")

        platform = request.query_params.get("platform")
        if platform:
            qs = qs.filter(source__platform=platform)

        processed = request.query_params.get("processed")
        if processed is not None:
            qs = qs.filter(is_processed=processed.lower() == "true")

        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(SocialLeadSerializer(page, many=True).data)


# ── Facebook Webhook ──────────────────────────────────────────────────────────


class FacebookWebhookView(APIView):
    """
    Receives and verifies Facebook Lead Ads webhook events.

    GET  — hub.challenge verification (Facebook verifies the endpoint on setup)
    POST — lead notification events
    """

    permission_classes = [AllowAny]

    def get(self, request):
        """Facebook sends a GET to verify the webhook endpoint."""
        mode = request.query_params.get("hub.mode")
        token = request.query_params.get("hub.verify_token")
        challenge = request.query_params.get("hub.challenge")

        if mode == "subscribe" and token:
            # Find a source whose verify_token matches
            source = SocialLeadSource.objects.filter(
                platform=SocialLeadSource.PLATFORM_FACEBOOK,
                webhook_verify_token=token,
                is_active=True,
            ).first()
            if source:
                return Response(int(challenge), status=status.HTTP_200_OK)

        return Response({"error": "verification_failed"}, status=status.HTTP_403_FORBIDDEN)

    def post(self, request):
        """Facebook fires a POST for each new lead submission."""
        # Verify HMAC-SHA256 signature
        signature = request.headers.get("X-Hub-Signature-256", "")
        app_secret = getattr(settings, "FACEBOOK_APP_SECRET", "")
        if app_secret and signature:
            body = request.body
            expected = "sha256=" + hmac.new(
                app_secret.encode(), body, hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(signature, expected):
                logger.warning("facebook.webhook.invalid_signature")
                return Response({"error": "invalid_signature"}, status=status.HTTP_403_FORBIDDEN)

        try:
            payload = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return Response({"error": "invalid_json"}, status=status.HTTP_400_BAD_REQUEST)

        if payload.get("object") != "page":
            return Response({"status": "ignored"})

        count = FacebookLeadService.handle_webhook(payload)
        logger.info("facebook.webhook.processed", extra={"leads_created": count})
        return Response({"status": "ok", "leads_created": count})


# ── LinkedIn Manual Sync ──────────────────────────────────────────────────────


class LinkedInSyncView(APIView):
    """
    Trigger a manual LinkedIn lead sync for a specific source.
    Normally this runs automatically every 15 minutes via Celery beat.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, website_id, source_id):
        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)
        try:
            source = SocialLeadSource.objects.get(
                id=source_id,
                website=website,
                platform=SocialLeadSource.PLATFORM_LINKEDIN,
            )
        except SocialLeadSource.DoesNotExist:
            return Response({"error": "source_not_found"}, status=status.HTTP_404_NOT_FOUND)

        from apps.social_leads.services.lead_processor import LinkedInLeadService
        count = LinkedInLeadService.sync_source(source)
        return Response({"status": "ok", "leads_imported": count})


# ── X CSV Import ──────────────────────────────────────────────────────────────


class XCSVImportView(APIView):
    """
    Import leads from an X (Twitter) Ads Manager CSV export.
    Expects JSON body: {"rows": [{"name": "...", "email": "...", "phone": "..."}, ...]}
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, website_id):
        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)
        rows = request.data.get("rows", [])
        if not isinstance(rows, list) or not rows:
            return Response(
                {"error": "rows must be a non-empty list"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.social_leads.services.lead_processor import XLeadService
        count = XLeadService.import_csv(website, rows)
        return Response({"status": "ok", "leads_imported": count})
