from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from apps.audits.models import Audit
from apps.audits.api.v1.serializers import AuditSerializer, AuditListSerializer
from apps.websites.services.website_service import WebsiteService
from core.exceptions import AuditInProgress, ResourceNotFound


class AuditRunView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, website_id):
        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)

        # Check for running audit
        if Audit.objects.filter(website=website, status__in=["pending", "running"]).exists():
            raise AuditInProgress()

        audit = Audit.objects.create(website=website, triggered_by=request.user)

        from apps.audits.tasks import run_website_audit
        run_website_audit.delay(str(website.id), str(audit.id))

        return Response({"audit_id": str(audit.id), "status": "pending"}, status=status.HTTP_202_ACCEPTED)


class AuditStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        running = Audit.objects.filter(
            website_id=website_id, status__in=["pending", "running"]
        ).first()
        if not running:
            return Response({"running": False})
        return Response({"running": True, "audit_id": str(running.id), "status": running.status})


class AuditLatestView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        audit = Audit.objects.filter(website_id=website_id, status="completed").first()
        if not audit:
            raise ResourceNotFound("No completed audits found.")
        return Response(AuditSerializer(audit).data)


class AuditHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        audits = Audit.objects.filter(website_id=website_id)
        return Response(AuditListSerializer(audits, many=True).data)


class AuditDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id, audit_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        try:
            audit = Audit.objects.get(id=audit_id, website_id=website_id)
        except Audit.DoesNotExist:
            raise ResourceNotFound("Audit not found.")
        return Response(AuditSerializer(audit).data)
