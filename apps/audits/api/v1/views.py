from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from apps.audits.models import Audit, SEOGraderIssue
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
        from django.conf import settings

        # In dev mode or when no Celery broker is configured, run in a thread
        broker = getattr(settings, "CELERY_BROKER_URL", "")
        if not broker or broker.startswith("memory://"):
            import threading
            t = threading.Thread(
                target=run_website_audit,
                args=(str(website.id), str(audit.id)),
                daemon=True,
            )
            t.start()
        else:
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


class SEOGraderView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        audit = Audit.objects.filter(website_id=website_id, status="completed").first()
        if not audit:
            return Response({"grader": None, "categories": []})

        grader = audit.raw_data.get("grader", {})
        issues = SEOGraderIssue.objects.filter(audit=audit)

        # Group by category
        from collections import OrderedDict
        cats = OrderedDict()
        for issue in issues:
            if issue.category not in cats:
                cats[issue.category] = {"total": 0, "deployed": 0, "items": []}
            cats[issue.category]["total"] += 1
            if issue.deployed:
                cats[issue.category]["deployed"] += 1
            cats[issue.category]["items"].append({
                "id": issue.id,
                "page_url": issue.page_url,
                "original_value": issue.original_value,
                "original_length": issue.original_length,
                "suggested_fix": issue.suggested_fix,
                "suggested_length": issue.suggested_length,
                "deployed": issue.deployed,
            })

        # Build category labels
        category_labels = dict(SEOGraderIssue.CATEGORIES)
        categories = []
        for cat_key, data in cats.items():
            categories.append({
                "key": cat_key,
                "label": category_labels.get(cat_key, cat_key),
                "total": data["total"],
                "deployed": data["deployed"],
                "items": data["items"],
            })

        total_issues = sum(c["total"] for c in categories)
        deployed_count = sum(c["deployed"] for c in categories)

        return Response({
            "grader": {
                "score": grader.get("grader_score", 0),
                "total_pages": grader.get("total_pages", 0),
                "total_issues": total_issues,
                "deployed": deployed_count,
                "not_deployed": total_issues - deployed_count,
                "flawless_pages": grader.get("flawless_pages", 0),
            },
            "categories": categories,
        })


class SEOGraderDeployView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, website_id, issue_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        try:
            issue = SEOGraderIssue.objects.get(id=issue_id, audit__website_id=website_id)
        except SEOGraderIssue.DoesNotExist:
            raise ResourceNotFound("Grader issue not found.")

        issue.deployed = not issue.deployed
        issue.save(update_fields=["deployed"])
        return Response({"id": issue.id, "deployed": issue.deployed})
