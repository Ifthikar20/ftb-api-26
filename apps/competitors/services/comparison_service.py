from apps.competitors.models import Competitor


class ComparisonService:
    @staticmethod
    def get_comparison_matrix(*, website_id: str) -> dict:
        """Return side-by-side comparison data for all competitors."""
        competitors = Competitor.objects.filter(website_id=website_id).prefetch_related("snapshots")
        result = []
        for comp in competitors:
            latest = comp.snapshots.first()
            result.append({
                "id": str(comp.id),
                "name": comp.name,
                "url": comp.competitor_url,
                "threat_level": comp.threat_level,
                "estimated_traffic": comp.estimated_traffic,
                "domain_authority": comp.domain_authority,
                "latest_snapshot": {
                    "traffic": latest.traffic_estimate if latest else None,
                    "keywords": latest.keyword_count if latest else None,
                    "backlinks": latest.backlink_count if latest else None,
                } if latest else None,
            })
        return {"competitors": result}
