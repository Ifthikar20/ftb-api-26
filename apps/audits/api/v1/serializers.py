from rest_framework import serializers

from apps.audits.models import Audit, AuditIssue


class AuditIssueSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditIssue
        fields = ["id", "category", "severity", "title", "description", "recommendation", "resolved", "impact_score"]


class AuditSerializer(serializers.ModelSerializer):
    issues = AuditIssueSerializer(many=True, read_only=True)

    class Meta:
        model = Audit
        fields = [
            "id", "status", "overall_score", "seo_score", "performance_score",
            "mobile_score", "security_score", "content_score", "triggered_at",
            "completed_at", "report_url", "issues",
        ]
        read_only_fields = fields


class AuditListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Audit
        fields = [
            "id", "status", "overall_score", "seo_score", "performance_score",
            "triggered_at", "completed_at",
        ]
