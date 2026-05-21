"""
API for the per-user RAG knowledge base.

All endpoints are website-scoped via TenantScopedAPIView. The user's
identity comes from request.user — chunks are insulated from one user
to another even within the same website (rare in practice, but the
unique constraint on KnowledgeSource enforces it).
"""
from rest_framework import status
from rest_framework.response import Response

from apps.rag.api.v1.serializers import (
    HitSerializer,
    IngestURLSerializer,
    KnowledgeChunkSerializer,
    KnowledgeSourceSerializer,
    RetrieveSerializer,
)
from apps.rag.models import KnowledgeChunk, KnowledgeSource
from apps.rag.services.retriever import retrieve
from core.resilience import TokenBucket
from core.views.base import TenantScopedAPIView


def _ingest_bucket(user_id) -> TokenBucket:
    """
    Per-user token bucket for RAG ingest. Caps abuse where one tenant
    queues huge crawl jobs back-to-back to either rack up embedding cost
    or use the server as a scraper proxy.

    Steady state: 30/min. Burst: 10. Refill is continuous so a real user
    triggering an "Add URL" ten times in a row succeeds; a script firing
    at 100 RPS gets throttled within seconds.
    """
    return TokenBucket(
        name=f"rag-ingest:{user_id}",
        capacity=10,
        refill_per_second=0.5,  # 30/min steady state
    )


def _retrieve_bucket(user_id) -> TokenBucket:
    """Per-user bucket for the cosine-similarity endpoint."""
    return TokenBucket(
        name=f"rag-retrieve:{user_id}",
        capacity=20,
        refill_per_second=2.0,  # 120/min steady state
    )


class KnowledgeSourceListView(TenantScopedAPIView):
    """GET = list sources for (user, website). POST = enqueue ingest."""

    def get(self, request, website_id):
        website = self.get_website(website_id)
        sources = KnowledgeSource.objects.filter(
            user=request.user, website=website,
        ).order_by("-created_at")
        return Response(KnowledgeSourceSerializer(sources, many=True).data)

    def post(self, request, website_id):
        website = self.get_website(website_id)

        # Per-user throttle. Burst of 10, refills at 30/min. Crawl jobs
        # consume more capacity since they fan out internally.
        serializer = IngestURLSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        cost = 5 if data.get("crawl") else 1
        if not _ingest_bucket(request.user.id).try_acquire(cost):
            return Response(
                {"error": "Rate limit exceeded for RAG ingest. "
                          "Slow down and retry shortly."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        from apps.rag.tasks import ingest_site_task, ingest_url_task

        if data.get("crawl"):
            ingest_site_task.delay(
                user_id=request.user.id,
                website_id=str(website.id),
                seed_url=data["url"],
                page_cap=data["page_cap"],
                depth=data["depth"],
            )
            return Response(
                {"queued": True, "mode": "crawl", "seed_url": data["url"]},
                status=status.HTTP_202_ACCEPTED,
            )

        ingest_url_task.delay(
            user_id=request.user.id,
            website_id=str(website.id),
            url=data["url"],
            kind=data["kind"],
            title=data.get("title", ""),
        )
        return Response(
            {"queued": True, "mode": "single", "url": data["url"]},
            status=status.HTTP_202_ACCEPTED,
        )


class KnowledgeSourceDetailView(TenantScopedAPIView):
    """GET / DELETE a single source (and its chunks)."""

    def get(self, request, website_id, source_id):
        website = self.get_website(website_id)
        source = self.get_tenant_object(
            KnowledgeSource.objects.filter(user=request.user, website=website),
            id=source_id,
        )
        chunks = KnowledgeChunk.objects.filter(source=source).order_by("chunk_index")
        return Response({
            "source": KnowledgeSourceSerializer(source).data,
            "chunks": KnowledgeChunkSerializer(chunks, many=True).data,
        })

    def delete(self, request, website_id, source_id):
        website = self.get_website(website_id)
        source = self.get_tenant_object(
            KnowledgeSource.objects.filter(user=request.user, website=website),
            id=source_id,
        )
        source.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RetrieveView(TenantScopedAPIView):
    """POST a query, get top-k chunks back. Used by the prompt previewer + clients."""

    def post(self, request, website_id):
        website = self.get_website(website_id)

        # Each retrieval call costs an embedding API call for the query.
        # Throttle to keep that cost bounded per-tenant.
        if not _retrieve_bucket(request.user.id).try_acquire():
            return Response(
                {"error": "Rate limit exceeded for retrieval. "
                          "Slow down and retry shortly."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        serializer = RetrieveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        hits = retrieve(
            user=request.user, website=website,
            query=data["query"], top_k=data["top_k"],
            kinds=data.get("kinds") or None,
        )
        return Response({
            "query": data["query"],
            "hits": HitSerializer(hits, many=True).data,
        })
