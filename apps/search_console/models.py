import uuid

from django.db import models

from core.mixins.timestamp_mixin import TimestampMixin


class GscMetricsBase(TimestampMixin):
    """Shared metric columns for Search Analytics rows.

    ctr and position are stored as reported by Google for the row's own
    dimension slice. Aggregations across rows must recompute ctr from
    clicks/impressions and weight position by impressions.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date = models.DateField()
    clicks = models.IntegerField(default=0)
    impressions = models.IntegerField(default=0)
    ctr = models.FloatField(default=0.0)
    position = models.FloatField(default=0.0)

    class Meta:
        abstract = True


class GscDailyTotal(GscMetricsBase):
    """Site-level daily totals from a dimensions=["date"] query.

    Source of truth for summary/timeseries endpoints: query-dimension
    rows undercount because Google anonymizes long-tail queries.
    """

    website = models.ForeignKey(
        "websites.Website", on_delete=models.CASCADE, related_name="gsc_daily_totals"
    )

    class Meta:
        db_table = "search_console_dailytotal"
        unique_together = [("website", "date")]
        indexes = [models.Index(fields=["website", "date"])]

    def __str__(self):
        return f"GscDailyTotal({self.website_id}, {self.date})"


class GscQueryStat(GscMetricsBase):
    """Per-query daily metrics from a dimensions=["date", "query"] query."""

    website = models.ForeignKey(
        "websites.Website", on_delete=models.CASCADE, related_name="gsc_query_stats"
    )
    query = models.CharField(max_length=512)

    class Meta:
        db_table = "search_console_querystat"
        unique_together = [("website", "date", "query")]
        indexes = [
            models.Index(fields=["website", "date"]),
            models.Index(fields=["website", "query", "date"]),
        ]

    def __str__(self):
        return f"GscQueryStat({self.website_id}, {self.date}, {self.query[:40]})"


class GscPageStat(GscMetricsBase):
    """Per-page daily metrics from a dimensions=["date", "page"] query."""

    website = models.ForeignKey(
        "websites.Website", on_delete=models.CASCADE, related_name="gsc_page_stats"
    )
    page = models.CharField(max_length=1000)

    class Meta:
        db_table = "search_console_pagestat"
        unique_together = [("website", "date", "page")]
        indexes = [
            models.Index(fields=["website", "date"]),
        ]

    def __str__(self):
        return f"GscPageStat({self.website_id}, {self.date}, {self.page[:60]})"
