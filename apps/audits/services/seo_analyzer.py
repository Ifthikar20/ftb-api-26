import logging
import requests
from apps.audits.models import Audit, AuditIssue

logger = logging.getLogger("apps")


class SEOAnalyzer:
    @staticmethod
    def analyze(*, website, audit: Audit) -> dict:
        """Perform SEO analysis on the website."""
        issues = []
        score = 100

        try:
            response = requests.get(website.url, timeout=15)
            content = response.text

            # Check for meta description
            if "<meta name=\"description\"" not in content.lower():
                score -= 10
                AuditIssue.objects.create(
                    audit=audit,
                    category="seo",
                    severity="warning",
                    title="Missing meta description",
                    description="No meta description tag found on the homepage.",
                    recommendation="Add a meta description tag with 150-160 characters.",
                    impact_score=8,
                )

            # Check for title tag
            if "<title>" not in content.lower():
                score -= 15
                AuditIssue.objects.create(
                    audit=audit,
                    category="seo",
                    severity="critical",
                    title="Missing title tag",
                    description="No <title> tag found on the homepage.",
                    recommendation="Add a descriptive title tag.",
                    impact_score=15,
                )

            # Check for HTTPS
            if not website.url.startswith("https://"):
                score -= 20
                AuditIssue.objects.create(
                    audit=audit,
                    category="security",
                    severity="critical",
                    title="Site not using HTTPS",
                    description="The site is served over HTTP, not HTTPS.",
                    recommendation="Install an SSL certificate and redirect all traffic to HTTPS.",
                    impact_score=20,
                )

        except requests.RequestException as e:
            logger.error(f"SEO analysis failed for {website.url}: {e}")
            score = 0

        return {"score": max(0, score), "security_score": score, "content_score": score}
