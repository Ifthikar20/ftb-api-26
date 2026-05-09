"""REST endpoints for Content Studio."""
from __future__ import annotations

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status as drf_status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.content_studio.api.v1.serializers import (
    ContentBriefSerializer,
    ContentDraftSerializer,
    PublishLogSerializer,
    PublishTargetSerializer,
    ROIAttributionSerializer,
)
from apps.content_studio.models import (
    BriefStatus,
    ContentBrief,
    ContentDraft,
    DraftStatus,
    PublishTarget,
    ROIAttribution,
)
from apps.content_studio.services.publish_adapters.export import serialize_draft
from core.exceptions import ResourceNotFound
from core.views import TenantScopedAPIView, TenantScopedListAPIView


def _brief_for_user(user, brief_id):
    from apps.websites.services.website_service import WebsiteService
    try:
        brief = ContentBrief.objects.select_related("website").get(id=brief_id)
    except ContentBrief.DoesNotExist as exc:
        raise ResourceNotFound("ContentBrief not found.") from exc
    WebsiteService.get_for_user(user=user, website_id=brief.website_id)
    return brief


def _draft_for_user(user, draft_id):
    from apps.websites.services.website_service import WebsiteService
    try:
        draft = ContentDraft.objects.select_related("website", "brief").get(id=draft_id)
    except ContentDraft.DoesNotExist as exc:
        raise ResourceNotFound("ContentDraft not found.") from exc
    WebsiteService.get_for_user(user=user, website_id=draft.website_id)
    return draft


def _target_for_user(user, target_id):
    from apps.websites.services.website_service import WebsiteService
    try:
        target = PublishTarget.objects.select_related("website").get(id=target_id)
    except PublishTarget.DoesNotExist as exc:
        raise ResourceNotFound("PublishTarget not found.") from exc
    WebsiteService.get_for_user(user=user, website_id=target.website_id)
    return target


class WebsiteBriefsView(TenantScopedListAPIView):
    def get(self, request, website_id):
        website = self.get_website(website_id)
        qs = ContentBrief.objects.filter(website=website)
        status_q = request.query_params.get("status")
        if status_q:
            qs = qs.filter(status=status_q)
        fmt = request.query_params.get("format")
        if fmt:
            qs = qs.filter(target_format=fmt)
        gap = request.query_params.get("gap_type")
        if gap:
            qs = qs.filter(gap_type=gap)
        qs = qs.order_by("-impact_score", "-created_at")
        return self.paginated_response(qs, ContentBriefSerializer)


class BriefDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, brief_id):
        brief = _brief_for_user(request.user, brief_id)
        return Response(ContentBriefSerializer(brief).data)


class BriefDraftView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, brief_id):
        brief = _brief_for_user(request.user, brief_id)
        from apps.content_studio.tasks import draft_content as draft_task
        try:
            draft_task.delay(str(brief.id))
            queued = True
        except Exception:
            queued = False
        if not queued:
            from apps.content_studio.services.drafter import draft_content
            draft = draft_content(str(brief.id))
            return Response(
                ContentDraftSerializer(draft).data,
                status=drf_status.HTTP_202_ACCEPTED,
            )
        return Response(
            {"status": "queued", "brief_id": str(brief.id)},
            status=drf_status.HTTP_202_ACCEPTED,
        )


class BriefSkipView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, brief_id):
        brief = _brief_for_user(request.user, brief_id)
        brief.status = BriefStatus.SKIPPED.value
        brief.save(update_fields=["status", "updated_at"])
        return Response(ContentBriefSerializer(brief).data)


class DraftDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, draft_id):
        draft = _draft_for_user(request.user, draft_id)
        return Response(ContentDraftSerializer(draft).data)

    def patch(self, request, draft_id):
        draft = _draft_for_user(request.user, draft_id)
        ser = ContentDraftSerializer(draft, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        # Allow editing title / body / status (limited transitions).
        for field in ("title", "body_markdown", "body_html", "json_ld", "status"):
            if field in ser.validated_data:
                setattr(draft, field, ser.validated_data[field])
        # If body changed without explicit status, mark as edited.
        if "status" not in ser.validated_data and (
            "body_markdown" in ser.validated_data or "title" in ser.validated_data
        ):
            draft.status = DraftStatus.EDITED.value
        draft.save()
        return Response(ContentDraftSerializer(draft).data)


class DraftRegenerateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, draft_id):
        draft = _draft_for_user(request.user, draft_id)
        from apps.content_studio.services.drafter import draft_content
        new_draft = draft_content(str(draft.brief_id), regenerate=True)
        return Response(ContentDraftSerializer(new_draft).data)


class DraftApproveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, draft_id):
        draft = _draft_for_user(request.user, draft_id)
        draft.status = DraftStatus.APPROVED.value
        draft.save(update_fields=["status", "updated_at"])
        return Response(ContentDraftSerializer(draft).data)


class DraftPublishView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, draft_id):
        draft = _draft_for_user(request.user, draft_id)
        target_id = request.data.get("target_id")
        if not target_id:
            return Response({"detail": "target_id required."}, status=400)
        target = _target_for_user(request.user, target_id)
        if target.website_id != draft.website_id:
            return Response({"detail": "target/draft mismatch."}, status=400)
        from apps.content_studio.tasks import publish_draft as publish_task
        try:
            publish_task.delay(str(draft.id), str(target.id))
            return Response({"status": "queued"}, status=drf_status.HTTP_202_ACCEPTED)
        except Exception:
            log_id = publish_task.run(str(draft.id), str(target.id))
            return Response({"status": "submitted", "log_id": log_id})


class DraftExportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, draft_id):
        draft = _draft_for_user(request.user, draft_id)
        fmt = request.query_params.get("format", "md")
        payload = serialize_draft(draft, fmt=fmt)
        resp = HttpResponse(payload["body"], content_type=payload["content_type"])
        resp["Content-Disposition"] = f"attachment; filename={payload['filename']}"
        return resp


class WebsitePublishTargetsView(TenantScopedListAPIView):
    def get(self, request, website_id):
        website = self.get_website(website_id)
        qs = PublishTarget.objects.filter(website=website).order_by("-is_default", "provider")
        return self.paginated_response(qs, PublishTargetSerializer)

    def post(self, request, website_id):
        website = self.get_website(website_id)
        ser = PublishTargetSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        target = PublishTarget.objects.create(
            website=website,
            provider=ser.validated_data["provider"],
            label=ser.validated_data.get("label", "") or "",
            config=ser.validated_data.get("config", {}) or {},
            is_default=ser.validated_data.get("is_default", False),
            is_active=ser.validated_data.get("is_active", True),
        )
        return Response(PublishTargetSerializer(target).data, status=drf_status.HTTP_201_CREATED)


class PublishTargetDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, target_id):
        target = _target_for_user(request.user, target_id)
        ser = PublishTargetSerializer(target, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        for f in ("provider", "label", "config", "is_default", "is_active"):
            if f in ser.validated_data:
                setattr(target, f, ser.validated_data[f])
        target.save()
        return Response(PublishTargetSerializer(target).data)

    def delete(self, request, target_id):
        target = _target_for_user(request.user, target_id)
        target.is_active = False
        target.save(update_fields=["is_active", "updated_at"])
        return Response(status=drf_status.HTTP_204_NO_CONTENT)


class WebsiteROIView(TenantScopedListAPIView):
    def get(self, request, website_id):
        website = self.get_website(website_id)
        qs = ROIAttribution.objects.filter(website=website).order_by("-measured_at")
        return self.paginated_response(qs, ROIAttributionSerializer)
