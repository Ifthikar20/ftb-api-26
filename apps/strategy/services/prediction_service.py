from apps.analytics.services.analytics_service import AnalyticsService


class PredictionService:
    @staticmethod
    def get_projections(*, website_id: str) -> dict:
        """Generate traffic and lead projections based on historical trends."""
        overview = AnalyticsService.get_overview(website_id=website_id, period="30d")

        current_visitors = overview.get("total_visitors", 0)
        growth_pct = overview.get("visitor_growth_pct", 0)

        # Simple linear projection
        monthly_growth_rate = 1 + (growth_pct / 100)

        return {
            "current_monthly_visitors": current_visitors,
            "projected_visitors": {
                "30d": int(current_visitors * monthly_growth_rate),
                "60d": int(current_visitors * (monthly_growth_rate ** 2)),
                "90d": int(current_visitors * (monthly_growth_rate ** 3)),
            },
            "confidence": "medium",
            "note": "Projections based on current growth trends.",
        }
