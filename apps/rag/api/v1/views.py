"""
API for the per-user RAG knowledge base.

All endpoints are website-scoped via TenantScopedAPIView. The user's
identity comes from request.user — chunks are insulated from one user
to another even within the same website (rare in practice, but the
unique constraint on KnowledgeSource enforces it).
"""
from rest_framework import status
from rest_framework.response import Response

from core.views.base import TenantScopedAPIView

from apps.rag.api.v1.serializers import (
    HitSerializer,
    IngestURLSerializer,
    KnowledgeChunkSerializer,
    KnowledgeSourceSerializer,
    RetrieveSerializer,
)
from apps.rag.models import KnowledgeChunk, KnowledgeSource
from apps.rag.services.retriever import retrieve


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
        serializer = IngestURLSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

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
