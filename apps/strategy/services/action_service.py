from django.utils import timezone

from apps.strategy.models import Action, Strategy
from core.exceptions import ResourceNotFound
from core.logging.audit_logger import audit_log


class ActionService:
    @staticmethod
    def get_this_weeks_actions(*, website_id: str) -> list:
        active_strategy = Strategy.objects.filter(website_id=website_id, status="active").first()
        if not active_strategy:
            return []
        return list(Action.objects.filter(strategy=active_strategy, week_number=1).order_by("id"))

    @staticmethod
    def update_action_status(*, action_id: str, website_id: str, status: str, user) -> Action:
        try:
            action = Action.objects.select_related("strategy__website").get(
                id=action_id, strategy__website_id=website_id
            )
        except Action.DoesNotExist:
            raise ResourceNotFound("Action not found.") from None

        action.status = status
        if status == "done":
            action.completed_at = timezone.now()
        action.save(update_fields=["status", "completed_at", "updated_at"])

        audit_log("action.updated", user=user, metadata={"action_id": str(action_id), "status": status})

        # Update strategy completion
        strategy = action.strategy
        total = strategy.actions.count()
        done = strategy.actions.filter(status="done").count()
        strategy.completion_pct = int((done / total) * 100) if total > 0 else 0
        strategy.save(update_fields=["completion_pct"])

        return action
