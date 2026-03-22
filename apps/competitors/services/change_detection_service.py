import logging

from django.utils import timezone

from apps.competitors.models import Competitor, CompetitorChange

logger = logging.getLogger("apps")


class ChangeDetectionService:
    @staticmethod
    def detect_changes(*, competitor: Competitor) -> list:
        """Compare latest snapshot to previous and detect changes."""
        snapshots = competitor.snapshots.order_by("-captured_at")[:2]
        if len(snapshots) < 2:
            return []

        latest, previous = snapshots[0], snapshots[1]
        changes = []

        if latest.traffic_estimate and previous.traffic_estimate:
            delta = latest.traffic_estimate - previous.traffic_estimate
            if abs(delta) > previous.traffic_estimate * 0.1:  # >10% change
                change = CompetitorChange.objects.create(
                    competitor=competitor,
                    change_type="ranking_change",
                    detail={
                        "traffic_delta": delta,
                        "previous": previous.traffic_estimate,
                        "current": latest.traffic_estimate,
                    },
                    detected_at=timezone.now(),
                )
                changes.append(change)

        return changes
