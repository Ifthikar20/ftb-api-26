import logging
import requests
from apps.audits.models import Audit, AuditIssue

logger = logging.getLogger("apps")


class ContentAnalyzer:
    @staticmethod
    def analyze(*, website, audit: Audit) -> dict:
        """Analyze content quality and structure."""
        score = 100
        try:
            response = requests.get(website.url, timeout=15)
            content = response.text

            if "<h1" not in content.lower():
                score -= 10
                AuditIssue.objects.create(
                    audit=audit,
                    category="content",
                    severity="warning",
                    title="Missing H1 heading",
                    description="No H1 tag found. H1 helps search engines understand the page topic.",
                    recommendation="Add a single, descriptive H1 heading to the page.",
                    impact_score=8,
                )
        except requests.RequestException as e:
            logger.error(f"Content analysis failed: {e}")
            score = 0

        return {"score": max(0, score)}
