"""DRF serializers for the claim_verifier API."""
from rest_framework import serializers

from apps.brand_vault.api.v1.serializers import BrandFactSerializer
from apps.claim_verifier.models import Claim, ClaimMismatch


class ClaimSerializer(serializers.ModelSerializer):
    provider = serializers.CharField(source="result.provider", read_only=True)
    prompt = serializers.CharField(source="result.prompt", read_only=True)

    class Meta:
        model = Claim
        fields = (
            "id", "result", "audit", "website",
            "text", "subject", "predicate", "object",
            "confidence",
            "provider", "prompt",
            "created_at",
        )
        read_only_fields = fields


class ClaimMismatchSerializer(serializers.ModelSerializer):
    claim = ClaimSerializer(read_only=True)
    matched_fact = BrandFactSerializer(read_only=True)

    class Meta:
        model = ClaimMismatch
        fields = (
            "id", "claim", "matched_fact",
            "mismatch_type", "severity",
            "factual_divergence", "audience_reach",
            "explanation",
            "dismissed", "dismissed_at",
            "created_at",
        )
        read_only_fields = fields


class ClaimDetailSerializer(serializers.ModelSerializer):
    mismatch = ClaimMismatchSerializer(read_only=True)
    provider = serializers.CharField(source="result.provider", read_only=True)
    prompt = serializers.CharField(source="result.prompt", read_only=True)

    class Meta:
        model = Claim
        fields = (
            "id", "result", "audit", "website",
            "text", "subject", "predicate", "object",
            "confidence",
            "provider", "prompt",
            "mismatch",
            "created_at",
        )
        read_only_fields = fields
