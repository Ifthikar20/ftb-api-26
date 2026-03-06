from django.utils import timezone
from apps.billing.models import Subscription, UsageRecord


class UsageService:
    @staticmethod
    def get_current_usage(*, user) -> dict:
        """Return current period usage metrics."""
        try:
            subscription = user.subscription
        except Subscription.DoesNotExist:
            return {}

        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        usage = {}
        for record in UsageRecord.objects.filter(
            subscription=subscription,
            period_start__lte=now.date(),
            period_end__gte=now.date(),
        ):
            usage[record.metric] = record.count

        return usage

    @staticmethod
    def increment(*, user, metric: str, amount: int = 1) -> None:
        """Increment a usage counter for the current billing period."""
        try:
            subscription = user.subscription
        except Subscription.DoesNotExist:
            return

        now = timezone.now()
        period_start = now.replace(day=1).date()
        period_end = (period_start.replace(month=period_start.month % 12 + 1, day=1)
                      if period_start.month < 12
                      else period_start.replace(year=period_start.year + 1, month=1, day=1))

        record, _ = UsageRecord.objects.get_or_create(
            subscription=subscription,
            metric=metric,
            period_start=period_start,
            defaults={"period_end": period_end, "count": 0},
        )
        UsageRecord.objects.filter(pk=record.pk).update(count=record.count + amount)
