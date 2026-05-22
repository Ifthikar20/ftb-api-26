"""REST endpoints for the Brand Vault."""
from __future__ import annotations

import csv
import io
from collections import Counter, defaultdict

from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.brand_vault.api.v1.serializers import (
    BrandFactDetailSerializer,
    BrandFactEditSerializer,
    BrandFactSerializer,
    FactImportItemSerializer,
    FactRevisionSerializer,
    ToneSampleSerializer,
)
from apps.brand_vault.models import BrandFact, FactRevision, FactStatus, ToneSample
from apps.brand_vault.services import fact_versioning
from apps.brand_vault.services.embeddings import embed_text
from apps.brand_vault.services.fact_versioning import record_creation
from core.exceptions import ResourceNotFound
from core.views import TenantScopedAPIView, TenantScopedListAPIView

# ── Standard B2B fact coverage ─────────────────────────────────────────────
# Used by WebsiteCoverageView to score how much of the "obvious" stuff a
# brand vault has on file. Predicates are matched case-insensitively with
# a substring check so "was founded" and "founded in" both count for
# the "founded" bucket.
STANDARD_BUCKETS: list[tuple[str, tuple[str, ...]]] = [
    ("founded", ("founded", "established", "started")),
    ("location", ("located", "headquarter", "based in", "office")),
    ("team", ("employee", "team size", "staff", "headcount")),
    ("product", ("offer", "sell", "build", "provide", "specialise", "specialize")),
    ("pricing", ("price", "cost", "subscription", "plan")),
    ("audience", ("serve", "audience", "customer", "target")),
    ("mission", ("mission", "vision", "value", "believe")),
    ("contact", ("contact", "email", "phone", "support")),
]


class WebsiteFactsView(TenantScopedListAPIView):
    """List facts for a website with status / product_line / topic filters."""

    def get(self, request, website_id):
        website = self.get_website(website_id)
        qs = BrandFact.objects.filter(website=website)

        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        product_line = request.query_params.get("product_line")
        if product_line:
            qs = qs.filter(product_line=product_line)

        topic = request.query_params.get("topic")
        if topic:
            qs = qs.filter(topic=topic)

        q = request.query_params.get("q")
        if q:
            qs = qs.filter(
                Q(subject__icontains=q) | Q(predicate__icontains=q)
                | Q(object__icontains=q),
            )

        only_current = request.query_params.get("only_current")
        if only_current and only_current.lower() in ("1", "true", "yes"):
            qs = qs.filter(version_to__isnull=True)

        qs = qs.order_by("-created_at")
        return self.paginated_response(qs, BrandFactSerializer)


def _get_fact_for_user(user, fact_id) -> BrandFact:
    from apps.websites.services.website_service import WebsiteService

    try:
        fact = BrandFact.objects.select_related("website").get(id=fact_id)
    except BrandFact.DoesNotExist as exc:
        raise ResourceNotFound("BrandFact not found.") from exc
    WebsiteService.get_for_user(user=user, website_id=fact.website_id)
    return fact


class FactDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, fact_id):
        fact = _get_fact_for_user(request.user, fact_id)
        return Response(BrandFactDetailSerializer(fact).data)


class FactApproveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, fact_id):
        fact = _get_fact_for_user(request.user, fact_id)
        fact = fact_versioning.approve_fact(str(fact.id), actor_user=request.user)
        return Response(BrandFactSerializer(fact).data)


class FactRejectView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, fact_id):
        fact = _get_fact_for_user(request.user, fact_id)
        fact = fact_versioning.reject_fact(str(fact.id), actor_user=request.user)
        return Response(BrandFactSerializer(fact).data)


class FactEditView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, fact_id):
        fact = _get_fact_for_user(request.user, fact_id)
        ser = BrandFactEditSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        new_fact = fact_versioning.supersede_fact(
            str(fact.id),
            ser.validated_data["subject"],
            ser.validated_data["predicate"],
            ser.validated_data["object"],
            actor_user=request.user,
        )
        return Response(BrandFactSerializer(new_fact).data, status=status.HTTP_201_CREATED)


class WebsiteExtractView(TenantScopedAPIView):
    """Trigger an LLM extraction pass over the website's KnowledgeChunks."""

    def post(self, request, website_id):
        website = self.get_website(website_id)
        try:
            from apps.brand_vault.tasks import extract_facts_for_website
            extract_facts_for_website.delay(str(website.id))
            queued = True
        except Exception:
            queued = False
        return Response({"queued": queued, "website_id": str(website.id)})


def _import_one(website, item: dict, *, actor_user=None) -> str:
    """Persist one validated fact item. Returns 'created' or 'skipped'."""
    subject = (item.get("subject") or "").strip()
    predicate = (item.get("predicate") or "").strip()
    obj = (item.get("object") or "").strip()
    if not subject or not predicate or not obj:
        raise ValueError("subject, predicate and object are required")
    exists = BrandFact.objects.filter(
        website=website,
        subject__iexact=subject,
        predicate__iexact=predicate,
        object__iexact=obj,
        version_to__isnull=True,
    ).exists()
    if exists:
        return "skipped"
    try:
        confidence = float(item.get("confidence") or 0.9)
    except (TypeError, ValueError):
        confidence = 0.9
    confidence = max(0.0, min(1.0, confidence))
    fact = BrandFact.objects.create(
        website=website,
        subject=subject[:300],
        predicate=predicate[:200],
        object=obj,
        product_line=(item.get("product_line") or "")[:120],
        topic=(item.get("topic") or "")[:120],
        source_url=(item.get("source_url") or "")[:1000],
        confidence=confidence,
        extracted_by="manual",
        status=FactStatus.APPROVED,
    )
    try:
        fact.embedding = embed_text(f"{subject} {predicate} {obj}")
        fact.save(update_fields=["embedding", "updated_at"])
    except Exception:
        pass
    record_creation(fact, actor_user=actor_user)
    return "created"


class WebsiteFactsImportView(TenantScopedAPIView):
    """Bulk-import manually authored facts (JSON body)."""

    parser_classes = [JSONParser]

    def post(self, request, website_id):
        website = self.get_website(website_id)
        raw = request.data.get("facts") if isinstance(request.data, dict) else None
        if not isinstance(raw, list):
            return Response(
                {"detail": "Body must be {\"facts\": [...]}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        created = 0
        skipped = 0
        errors: list[dict] = []
        for idx, item in enumerate(raw):
            ser = FactImportItemSerializer(data=item)
            if not ser.is_valid():
                errors.append({"index": idx, "errors": ser.errors})
                continue
            try:
                outcome = _import_one(website, ser.validated_data, actor_user=request.user)
            except Exception as exc:
                errors.append({"index": idx, "error": str(exc)})
                continue
            if outcome == "created":
                created += 1
            else:
                skipped += 1
        return Response({"created": created, "skipped": skipped, "errors": errors})


class WebsiteFactsImportCSVView(TenantScopedAPIView):
    """Bulk-import facts from a CSV file (multipart/form-data)."""

    parser_classes = [MultiPartParser, FormParser]

    EXPECTED_COLUMNS = (
        "subject", "predicate", "object",
        "product_line", "topic", "confidence", "source_url",
    )

    def post(self, request, website_id):
        website = self.get_website(website_id)
        f = request.FILES.get("file") or request.FILES.get("csv")
        if f is None:
            return Response(
                {"detail": "Upload a 'file' field with a CSV body."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            raw = f.read().decode("utf-8-sig", errors="replace")
        except Exception:
            return Response(
                {"detail": "Could not decode CSV as UTF-8."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        reader = csv.DictReader(io.StringIO(raw))
        created = 0
        skipped = 0
        errors: list[dict] = []
        for idx, row in enumerate(reader):
            data = {k: (row.get(k) or "").strip() for k in self.EXPECTED_COLUMNS}
            if data.get("confidence") in ("", None):
                data.pop("confidence", None)
            ser = FactImportItemSerializer(data=data)
            if not ser.is_valid():
                errors.append({"row": idx + 1, "errors": ser.errors})
                continue
            try:
                outcome = _import_one(website, ser.validated_data, actor_user=request.user)
            except Exception as exc:
                errors.append({"row": idx + 1, "error": str(exc)})
                continue
            if outcome == "created":
                created += 1
            else:
                skipped += 1
        return Response({"created": created, "skipped": skipped, "errors": errors})


class WebsiteToneSamplesView(TenantScopedListAPIView):
    """List ToneSample rows for a website (Phase 4 voice-guard input)."""

    def get(self, request, website_id):
        website = self.get_website(website_id)
        qs = ToneSample.objects.filter(website=website).order_by("-created_at")
        return self.paginated_response(qs, ToneSampleSerializer)


class WebsiteStatsView(TenantScopedAPIView):
    """Aggregate counts for the dashboard header."""

    def get(self, request, website_id):
        website = self.get_website(website_id)
        qs = BrandFact.objects.filter(website=website)

        by_status: Counter = Counter()
        by_product: Counter = Counter()
        by_topic: Counter = Counter()
        for s, pl, tp in qs.values_list("status", "product_line", "topic"):
            by_status[s] += 1
            if pl:
                by_product[pl] += 1
            if tp:
                by_topic[tp] += 1

        recent = qs.order_by("-created_at")[:5]
        recent_data = BrandFactSerializer(recent, many=True).data

        # Stale facts — anything approved/auto more than 180 days ago.
        stale_cutoff = timezone.now() - timezone.timedelta(days=180)
        stale = qs.filter(
            status__in=[FactStatus.APPROVED, FactStatus.AUTO],
            version_to__isnull=True,
            version_from__lt=stale_cutoff,
        ).count()

        # Last extraction timestamp — surface to the header so the user
        # knows when we last refreshed the vault.
        last = qs.order_by("-created_at").values_list("created_at", flat=True).first()

        return Response({
            "website_id": str(website.id),
            "total": sum(by_status.values()),
            "by_status": {
                FactStatus.PENDING.value: by_status.get(FactStatus.PENDING.value, 0),
                FactStatus.APPROVED.value: by_status.get(FactStatus.APPROVED.value, 0),
                FactStatus.REJECTED.value: by_status.get(FactStatus.REJECTED.value, 0),
                FactStatus.AUTO.value: by_status.get(FactStatus.AUTO.value, 0),
            },
            "by_product_line": dict(by_product.most_common(20)),
            "by_topic": dict(by_topic.most_common(20)),
            "stale_count": stale,
            "last_extracted_at": last.isoformat() if last else None,
            "recent": recent_data,
        })


class WebsiteBulkFactActionView(TenantScopedAPIView):
    """
    Batch-approve or batch-reject a list of fact ids.

    Body: ``{"ids": ["uuid", ...], "action": "approve"|"reject"}``.
    Skips ids that don't belong to this website and reports per-id
    outcomes so the UI can highlight any that failed.
    """

    def post(self, request, website_id):
        website = self.get_website(website_id)
        ids = request.data.get("ids") or []
        action = (request.data.get("action") or "").lower()
        if not isinstance(ids, list) or not ids:
            return Response({"detail": "ids must be a non-empty array."},
                            status=status.HTTP_400_BAD_REQUEST)
        if action not in ("approve", "reject"):
            return Response({"detail": "action must be 'approve' or 'reject'."},
                            status=status.HTTP_400_BAD_REQUEST)

        facts = list(BrandFact.objects.filter(website=website, id__in=ids))
        approved = []
        rejected = []
        errors = []
        for fact in facts:
            try:
                if action == "approve":
                    f = fact_versioning.approve_fact(str(fact.id), actor_user=request.user)
                    approved.append(str(f.id))
                else:
                    f = fact_versioning.reject_fact(str(fact.id), actor_user=request.user)
                    rejected.append(str(f.id))
            except Exception as exc:
                errors.append({"id": str(fact.id), "error": str(exc)})

        missing = sorted(set(map(str, ids)) - {str(f.id) for f in facts})
        return Response({
            "approved_ids": approved,
            "rejected_ids": rejected,
            "missing_ids": missing,
            "errors": errors,
        })


class FactUsageView(APIView):
    """
    Where has this fact actually been cited?

    We don't have a denormalised "uses" table yet, so this view
    answers conservatively by counting:
      - LLMRanking audits on the fact's website that completed after
        the fact's version_from (a heuristic — the fact was available
        as grounding when the audit ran).
      - ContentStudio drafts on the same website created after
        version_from.
    Plus the fact's own revision count, which is exact.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, fact_id):
        fact = _get_fact_for_user(request.user, fact_id)
        audit_count = 0
        draft_count = 0
        try:
            from apps.llm_ranking.models import LLMRankingAudit
            audit_count = LLMRankingAudit.objects.filter(
                website_id=fact.website_id,
                status="completed",
                completed_at__gte=fact.version_from,
            ).count()
        except Exception:
            pass
        try:
            from apps.content_studio.models import ContentDraft
            draft_count = ContentDraft.objects.filter(
                website_id=fact.website_id,
                created_at__gte=fact.version_from,
            ).count()
        except Exception:
            pass

        revisions = fact.revisions.count()
        return Response({
            "fact_id": str(fact.id),
            "audit_count": audit_count,
            "draft_count": draft_count,
            "revision_count": revisions,
            "since": fact.version_from.isoformat() if fact.version_from else None,
        })


class WebsiteContradictionsView(TenantScopedAPIView):
    """
    Surface facts that contradict each other — same subject + predicate,
    different object, both currently in force (approved/auto, no
    version_to). Critical for trust because downstream agents can be
    handed conflicting grounding.
    """

    def get(self, request, website_id):
        website = self.get_website(website_id)
        qs = BrandFact.objects.filter(
            website=website,
            status__in=[FactStatus.APPROVED, FactStatus.AUTO],
            version_to__isnull=True,
        )
        grouped: dict[tuple[str, str], list[BrandFact]] = defaultdict(list)
        for f in qs:
            key = (f.subject.strip().lower(), f.predicate.strip().lower())
            grouped[key].append(f)

        clusters = []
        for (_subject, _predicate), facts in grouped.items():
            if len(facts) < 2:
                continue
            objects = {f.object.strip().lower() for f in facts}
            if len(objects) < 2:
                continue
            clusters.append({
                "subject": facts[0].subject,
                "predicate": facts[0].predicate,
                "fact_count": len(facts),
                "facts": BrandFactSerializer(facts, many=True).data,
            })

        clusters.sort(key=lambda c: -c["fact_count"])
        return Response({
            "website_id": str(website.id),
            "cluster_count": len(clusters),
            "clusters": clusters,
        })


class WebsiteCoverageView(TenantScopedAPIView):
    """
    Score how complete the vault is against a standard B2B fact
    taxonomy (founded, location, team, product, pricing, audience,
    mission, contact). Each bucket counts approved/auto current facts
    whose predicate matches any of the bucket's keywords.
    """

    def get(self, request, website_id):
        website = self.get_website(website_id)
        qs = BrandFact.objects.filter(
            website=website,
            status__in=[FactStatus.APPROVED, FactStatus.AUTO],
            version_to__isnull=True,
        ).values_list("predicate", flat=True)

        predicates = [p.lower() for p in qs]
        buckets = []
        covered = 0
        for key, needles in STANDARD_BUCKETS:
            count = sum(1 for p in predicates if any(n in p for n in needles))
            if count > 0:
                covered += 1
            buckets.append({"key": key, "count": count, "covered": count > 0})

        score = round(100 * covered / len(STANDARD_BUCKETS)) if STANDARD_BUCKETS else 0
        return Response({
            "website_id": str(website.id),
            "score": score,
            "covered_buckets": covered,
            "total_buckets": len(STANDARD_BUCKETS),
            "buckets": buckets,
        })


class WebsiteRevisionsView(TenantScopedListAPIView):
    """Recent FactRevision rows for the History tab."""

    def get(self, request, website_id):
        website = self.get_website(website_id)
        qs = FactRevision.objects.filter(
            fact__website=website,
        ).select_related("actor_user", "fact").order_by("-created_at")
        action = request.query_params.get("action")
        if action:
            qs = qs.filter(action=action)
        return self.paginated_response(qs, FactRevisionSerializer)


class WebsiteExtractStatusView(TenantScopedAPIView):
    """
    Poll target for the extraction progress banner.

    We don't have per-task progress in Redis (the task just writes
    facts as it finds them), so the status proxy is the count of
    facts created in the last 10 minutes. Good enough for the UI to
    show "N new facts since you clicked Re-scan".
    """

    def get(self, request, website_id):
        website = self.get_website(website_id)
        since = timezone.now() - timezone.timedelta(minutes=10)
        recent = BrandFact.objects.filter(
            website=website,
            created_at__gte=since,
        ).count()
        last = BrandFact.objects.filter(
            website=website,
        ).order_by("-created_at").values_list("created_at", flat=True).first()
        return Response({
            "website_id": str(website.id),
            "recent_facts": recent,
            "last_extracted_at": last.isoformat() if last else None,
        })


class WebsiteToneSampleCreateView(TenantScopedAPIView):
    """Manually attach a tone-of-voice sample for this website."""

    parser_classes = [JSONParser]

    def post(self, request, website_id):
        website = self.get_website(website_id)
        text = (request.data.get("text") or "").strip()
        if not text:
            return Response({"detail": "text is required."},
                            status=status.HTTP_400_BAD_REQUEST)
        if len(text) > 4000:
            return Response({"detail": "Each sample must be 4000 chars or fewer."},
                            status=status.HTTP_400_BAD_REQUEST)
        import hashlib
        text_hash = hashlib.sha1(text.encode("utf-8")).hexdigest()  # noqa: S324
        sample, _ = ToneSample.objects.get_or_create(
            website=website,
            text_hash=text_hash,
            defaults={"text": text, "word_count": len(text.split())},
        )
        return Response(ToneSampleSerializer(sample).data,
                        status=status.HTTP_201_CREATED)


class ToneSampleDeleteView(APIView):
    """Remove one tone sample. Scoped to the user's own websites."""

    permission_classes = [IsAuthenticated]

    def delete(self, request, sample_id):
        from apps.websites.services.website_service import WebsiteService
        try:
            sample = ToneSample.objects.select_related("website").get(id=sample_id)
        except ToneSample.DoesNotExist as exc:
            raise ResourceNotFound("ToneSample not found.") from exc
        WebsiteService.get_for_user(user=request.user, website_id=sample.website_id)
        sample.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
