import logging
from django.utils import timezone

from apps.audits.models import Audit
from apps.audits.services.seo_analyzer import SEOAnalyzer
from apps.audits.services.performance_analyzer import PerformanceAnalyzer
from apps.audits.services.mobile_analyzer import MobileAnalyzer
from apps.audits.services.security_analyzer import SecurityAnalyzer
from apps.audits.services.content_analyzer import ContentAnalyzer

logger = logging.getLogger("apps")

# Scoring weights for the overall composite score
WEIGHTS = {
    "seo": 0.30,
    "performance": 0.25,
    "mobile": 0.15,
    "security": 0.15,
    "content": 0.15,
}


class AuditOrchestrator:
    @staticmethod
    def execute(*, website_id: str, audit: Audit) -> dict:
        """Run all 5 audit analyzers and compile weighted results."""
        from apps.websites.models import Website
        website = Website.objects.get(id=website_id)

        logger.info(f"Starting full audit for {website.url}")

        # Run each analyzer independently — one failure shouldn't kill the audit
        results = {}

        try:
            seo = SEOAnalyzer.analyze(website=website, audit=audit)
            results["seo_score"] = seo["score"]
        except Exception as e:
            logger.error(f"SEO analyzer failed: {e}")
            results["seo_score"] = 0

        try:
            perf = PerformanceAnalyzer.analyze(website=website, audit=audit)
            results["performance_score"] = perf["score"]
        except Exception as e:
            logger.error(f"Performance analyzer failed: {e}")
            results["performance_score"] = 0

        try:
            mobile = MobileAnalyzer.analyze(website=website, audit=audit)
            results["mobile_score"] = mobile["score"]
        except Exception as e:
            logger.error(f"Mobile analyzer failed: {e}")
            results["mobile_score"] = 0

        try:
            security = SecurityAnalyzer.analyze(website=website, audit=audit)
            results["security_score"] = security["score"]
        except Exception as e:
            logger.error(f"Security analyzer failed: {e}")
            results["security_score"] = 0

        try:
            content = ContentAnalyzer.analyze(website=website, audit=audit)
            results["content_score"] = content["score"]
        except Exception as e:
            logger.error(f"Content analyzer failed: {e}")
            results["content_score"] = 0

        # Weighted overall score
        overall = (
            results["seo_score"] * WEIGHTS["seo"]
            + results["performance_score"] * WEIGHTS["performance"]
            + results["mobile_score"] * WEIGHTS["mobile"]
            + results["security_score"] * WEIGHTS["security"]
            + results["content_score"] * WEIGHTS["content"]
        )
        results["overall_score"] = round(overall)

        logger.info(
            f"Audit complete for {website.url}: "
            f"overall={results['overall_score']} "
            f"seo={results['seo_score']} perf={results['performance_score']} "
            f"mobile={results['mobile_score']} security={results['security_score']} "
            f"content={results['content_score']}"
        )

        # Store raw data
        audit.raw_data = {
            "scores": results,
            "weights": WEIGHTS,
            "issue_count": audit.issues.count(),
        }
        audit.save(update_fields=["raw_data"])

        return results
