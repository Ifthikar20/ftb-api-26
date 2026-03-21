"""Conversion funnel analysis."""
import logging
from collections import OrderedDict

from django.db.models import Count, Q
from apps.analytics.models import PageEvent, CustomFunnel, Visitor
from core.utils.date_utils import get_date_range

logger = logging.getLogger("apps")


class FunnelService:
    @staticmethod
    def calculate_funnel(*, website_id: str, funnel_id: str = None, steps: list = None, period: str = "30d") -> dict:
        """
        Calculate conversion through a multi-step funnel.
        Steps can be URL patterns or event names.
        Returns visitors at each step + drop-off percentages.
        """
        if funnel_id:
            funnel = CustomFunnel.objects.get(id=funnel_id, website_id=website_id)
            steps = funnel.steps
            funnel_name = funnel.name
        else:
            funnel_name = "Ad-hoc Funnel"

        if not steps or len(steps) < 2:
            return {"error": "Funnel needs at least 2 steps"}

        start, end = get_date_range(period)

        results = []
        remaining_visitors = None

        for i, step in enumerate(steps):
            step_name = step.get("name", f"Step {i+1}")
            step_type = step.get("type", "url")  # "url" or "event"
            step_value = step.get("value", "")

            # Build query for this step
            q = Q(website_id=website_id, timestamp__range=(start, end))
            if step_type == "url":
                q &= Q(event_type="pageview", url__icontains=step_value)
            elif step_type == "event":
                q &= Q(event_type=step_value) | Q(event_name=step_value)

            # Get distinct visitors who hit this step
            step_visitors = set(
                PageEvent.objects.filter(q).values_list("visitor_id", flat=True).distinct()
            )

            # Intersect with previous step's visitors
            if remaining_visitors is not None:
                step_visitors = step_visitors & remaining_visitors

            remaining_visitors = step_visitors
            count = len(step_visitors)

            results.append({
                "step": i + 1,
                "name": step_name,
                "type": step_type,
                "value": step_value,
                "visitors": count,
            })

        # Calculate conversion rates and drop-off
        if results and results[0]["visitors"] > 0:
            top = results[0]["visitors"]
            for i, r in enumerate(results):
                r["conversion_pct"] = round(r["visitors"] / top * 100, 1)
                if i > 0:
                    prev = results[i - 1]["visitors"]
                    r["drop_off_pct"] = round((1 - r["visitors"] / prev) * 100, 1) if prev > 0 else 0
                else:
                    r["drop_off_pct"] = 0

        overall_conversion = 0
        if results and results[0]["visitors"] > 0:
            overall_conversion = round(results[-1]["visitors"] / results[0]["visitors"] * 100, 1)

        return {
            "name": funnel_name,
            "period": period,
            "steps": results,
            "overall_conversion_pct": overall_conversion,
            "total_entered": results[0]["visitors"] if results else 0,
            "total_completed": results[-1]["visitors"] if results else 0,
        }

    @staticmethod
    def list_funnels(*, website_id: str) -> list:
        """List all saved funnels for a website."""
        return list(
            CustomFunnel.objects.filter(website_id=website_id)
            .values("id", "name", "steps", "created_at")
            .order_by("-created_at")
        )

    @staticmethod
    def create_funnel(*, website_id: str, name: str, steps: list, user=None) -> dict:
        """Create a new funnel definition."""
        funnel = CustomFunnel.objects.create(
            website_id=website_id,
            name=name,
            steps=steps,
            created_by=user,
        )
        return {"id": str(funnel.id), "name": funnel.name, "steps": funnel.steps}
