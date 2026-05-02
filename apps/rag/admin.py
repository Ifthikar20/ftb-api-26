from django.contrib import admin

from apps.rag.models import KnowledgeChunk, KnowledgeSource


@admin.register(KnowledgeSource)
class KnowledgeSourceAdmin(admin.ModelAdmin):
    list_display = ("url", "user", "website", "kind", "status", "chunk_count", "last_ingested_at")
    list_filter = ("kind", "status")
    search_fields = ("url", "title")
    readonly_fields = ("content_hash", "chunk_count", "last_ingested_at", "created_at", "updated_at")


@admin.register(KnowledgeChunk)
class KnowledgeChunkAdmin(admin.ModelAdmin):
    list_display = ("source", "chunk_index", "section_label", "embedding_model", "token_count")
    list_filter = ("embedding_model", "source__kind")
    search_fields = ("text", "section_label")
    readonly_fields = (
        "embedding_model", "embedding_dim", "token_count", "created_at", "updated_at",
    )
