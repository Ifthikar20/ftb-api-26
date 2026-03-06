import logging
import time
import requests
from apps.audits.models import Audit, AuditIssue

logger = logging.getLogger("apps")


class PerformanceAnalyzer:
    @staticmethod
    def analyze(*, website, audit: Audit) -> dict:
        """Measure basic performance metrics."""
        score = 100

        try:
            start = time.monotonic()
            response = requests.get(website.url, timeout=30)
            ttfb_ms = (time.monotonic() - start) * 1000

            page_size_kb = len(response.content) / 1024

            if ttfb_ms > 1000:
                score -= 20
                AuditIssue.objects.create(
                    audit=audit,
                    category="performance",
                    severity="critical",
                    title="Slow Time to First Byte",
                    description=f"TTFB is {ttfb_ms:.0f}ms. Target is under 200ms.",
                    recommendation="Optimize server response time, use caching, or consider a CDN.",
                    impact_score=20,
                )

            if page_size_kb > 3000:
                score -= 15
                AuditIssue.objects.create(
                    audit=audit,
                    category="performance",
                    severity="warning",
                    title="Large page size",
                    description=f"Page is {page_size_kb:.0f}KB. Target is under 1500KB.",
                    recommendation="Optimize images, minify CSS/JS, remove unused code.",
                    impact_score=15,
                )

        except requests.RequestException as e:
            logger.error(f"Performance analysis failed for {website.url}: {e}")
            score = 0

        return {"score": max(0, score), "mobile_score": score}
