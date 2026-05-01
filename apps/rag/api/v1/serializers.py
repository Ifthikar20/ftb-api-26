from rest_framework import serializers

from apps.rag.models import KnowledgeChunk, KnowledgeSource


class KnowledgeSourceSerializer(serializers.ModelSerializer):
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = KnowledgeSource
        fields = [
            "id", "url", "title", "kind", "kind_display",
            "status", "status_display", "chunk_count",
            "error_message", "last_ingested_at", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "kind_display", "status", "status_display",
            "chunk_count", "error_message", "last_ingested_at",
            "created_at", "updated_at",
        ]


class IngestURLSerializer(serializers.Serializer):
    url = serializers.URLField(max_length=2000)
    kind = serializers.ChoiceField(
        choices=[c[0] for c in KnowledgeSource.KIND_CHOICES],
        required=False, default=KnowledgeSource.KIND_OTHER,
    )
    title = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")
    crawl = serializers.BooleanField(required=False, default=False)
    page_cap = serializers.IntegerField(required=False, default=12, min_value=1, max_value=50)
    depth = serializers.IntegerField(required=False, default=1, min_value=0, max_value=2)


class RetrieveSerializer(serializers.Serializer):
    query = serializers.CharField(max_length=2000)
    top_k = serializers.IntegerField(required=False, default=5, min_value=1, max_value=20)
    kinds = serializers.ListField(
        child=serializers.ChoiceField(choices=[c[0] for c in KnowledgeSource.KIND_CHOICES]),
        required=False, default=list,
    )


class HitSerializer(serializers.Serializer):
    chunk_id = serializers.CharField()
    source_id = serializers.CharField()
    source_url = serializers.CharField()
    source_kind = serializers.CharField()
    section_label = serializers.CharField()
    text = serializers.CharField()
    score = serializers.FloatField()


class KnowledgeChunkSerializer(serializers.ModelSerializer):
    source_url = serializers.CharField(source="source.url", read_only=True)

    class Meta:
        model = KnowledgeChunk
        fields = [
            "id", "source_id", "source_url", "chunk_index",
            "section_label", "text", "embedding_model", "embedding_dim",
            "token_count", "created_at",
        ]
        read_only_fields = fields
