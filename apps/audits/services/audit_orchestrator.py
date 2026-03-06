import logging
from django.utils import timezone

from apps.audits.models import Audit
from apps.audits.services.seo_analyzer import SEOAnalyzer
from apps.audits.services.performance_analyzer import PerformanceAnalyzer

logger = logging.getLogger("apps")


class AuditOrchestrator:
    @staticmethod
    def execute(*, website_id: str, audit: Audit) -> dict:
        """Run all audit checks and compile results."""
        from apps.websites.models import Website
        website = Website.objects.get(id=website_id)

        logger.info(f"Starting audit for {website.url}")

        seo_result = SEOAnalyzer.analyze(website=website, audit=audit)
        performance_result = PerformanceAnalyzer.analyze(website=website, audit=audit)

        overall_score = (seo_result["score"] + performance_result["score"]) // 2

        return {
            "overall_score": overall_score,
            "seo_score": seo_result["score"],
            "performance_score": performance_result["score"],
            "mobile_score": performance_result.get("mobile_score", 0),
            "security_score": seo_result.get("security_score", 0),
            "content_score": seo_result.get("content_score", 0),
        }
