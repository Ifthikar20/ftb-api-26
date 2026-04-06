import uuid

from django.db import models

from core.mixins.timestamp_mixin import TimestampMixin


class Visitor(TimestampMixin):
    """A unique visitor tracked by the pixel."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    website = models.ForeignKey(
        "websites.Website", on_delete=models.CASCADE, related_name="visitors"
    )
    fingerprint_hash = models.CharField(max_length=64, db_index=True)
    ip_hash = models.CharField(max_length=64, blank=True)  # Hashed, not raw IP (privacy)
    company_name = models.CharField(max_length=200, blank=True)
    geo_country = models.CharField(max_length=2, blank=True)
    geo_city = models.CharField(max_length=100, blank=True)
    device_type = models.CharField(max_length=20, blank=True)
    browser = models.CharField(max_length=50, blank=True)
    os = models.CharField(max_length=50, blank=True)
    first_seen = models.DateTimeField(auto_now_add=True, db_index=True)
    last_seen = models.DateTimeField(auto_now=True, db_index=True)
    visit_count = models.PositiveIntegerField(default=1)
    lead_score = models.IntegerField(default=0, db_index=True)

    class Meta:
        db_table = "analytics_visitor"
        unique_together = [("website", "fingerprint_hash")]
        indexes = [
            models.Index(fields=["website", "lead_score"]),
            models.Index(fields=["website", "last_seen"]),
        ]

    def __str__(self):
        return f"Visitor({self.fingerprint_hash[:8]}@{self.website.name})"


class Session(models.Model):
    """A single browsing session for a visitor."""

    visitor = models.ForeignKey(Visitor, on_delete=models.CASCADE, related_name="sessions")
    started_at = models.DateTimeField(db_index=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    page_count = models.PositiveIntegerField(default=0)
    entry_page = models.URLField(max_length=1000, blank=True)
    exit_page = models.URLField(max_length=1000, blank=True)
    source = models.CharField(max_length=100, blank=True)
    medium = models.CharField(max_length=100, blank=True)
    campaign = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = "analytics_session"

    def __str__(self):
        return f"Session({self.visitor_id}, {self.started_at})"


class PageEvent(TimestampMixin):
    """A single page event emitted by the tracking pixel."""

    EVENT_TYPES = [
        ("pageview", "Page View"),
        ("click", "Click"),
        ("form_submit", "Form Submit"),
        ("scroll", "Scroll"),
        ("session_end", "Session End"),
        ("custom", "Custom"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visitor = models.ForeignKey(Visitor, on_delete=models.CASCADE, related_name="events")
    website = models.ForeignKey(
        "websites.Website", on_delete=models.CASCADE, related_name="events"
    )
    session = models.ForeignKey(Session, null=True, on_delete=models.SET_NULL, related_name="events")
    url = models.URLField(max_length=2000)
    referrer = models.URLField(max_length=2000, blank=True)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES, default="pageview")
    event_name = models.CharField(max_length=100, blank=True)
    properties = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(db_index=True)
    scroll_depth = models.IntegerField(null=True, blank=True)
    time_on_page_ms = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "analytics_pageevent"
        indexes = [
            models.Index(fields=["website", "event_type", "timestamp"]),
            models.Index(fields=["visitor", "timestamp"]),
        ]

    def __str__(self):
        return f"PageEvent({self.event_type}: {self.url[:50]})"


class CustomFunnel(TimestampMixin):
    """User-defined conversion funnel."""

    website = models.ForeignKey(
        "websites.Website", on_delete=models.CASCADE, related_name="funnels"
    )
    name = models.CharField(max_length=200)
    steps = models.JSONField(default=list)
    created_by = models.ForeignKey(
        "accounts.User", null=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        db_table = "analytics_customfunnel"

    def __str__(self):
        return f"Funnel({self.name})"


class TrackedKeyword(TimestampMixin):
    """A keyword being tracked for rank monitoring."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    website = models.ForeignKey(
        "websites.Website", on_delete=models.CASCADE, related_name="tracked_keywords"
    )
    keyword = models.CharField(max_length=300, db_index=True)
    target_url = models.URLField(max_length=2000, blank=True)
    current_rank = models.IntegerField(null=True, blank=True)
    previous_rank = models.IntegerField(null=True, blank=True)
    best_rank = models.IntegerField(null=True, blank=True)
    search_volume = models.IntegerField(default=0)
    difficulty = models.IntegerField(default=0)  # 0-100

    class Meta:
        db_table = "analytics_trackedkeyword"
        unique_together = [("website", "keyword")]

    def __str__(self):
        return f"Keyword({self.keyword} #{self.current_rank})"


class TrackedLink(TimestampMixin):
    """
    A short tracked URL that redirects to a destination and records click attribution.
    Used in email campaigns and content to measure conversions.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    website = models.ForeignKey(
        "websites.Website", on_delete=models.CASCADE, related_name="tracked_links"
    )
    # Optional link to an email campaign
    campaign = models.ForeignKey(
        "leads.EmailCampaign", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="tracked_links",
    )
    destination_url = models.URLField(max_length=2000)
    tracking_key = models.CharField(max_length=32, unique=True, db_index=True)
    description = models.CharField(max_length=300, blank=True)
    click_count = models.IntegerField(default=0)
    conversion_count = models.IntegerField(default=0)

    class Meta:
        db_table = "analytics_trackedlink"

    def __str__(self):
        return f"TrackedLink({self.tracking_key} -> {self.destination_url[:60]})"


class LinkClick(TimestampMixin):
    """A single click on a TrackedLink."""

    tracked_link = models.ForeignKey(TrackedLink, on_delete=models.CASCADE, related_name="clicks")
    # Visitor may be null for anonymous clicks that we can't tie to a fingerprint
    visitor = models.ForeignKey(
        Visitor, null=True, blank=True, on_delete=models.SET_NULL, related_name="link_clicks"
    )
    # Optional back-reference to the campaign recipient (enables full-funnel attribution)
    campaign_recipient = models.ForeignKey(
        "leads.CampaignRecipient", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="link_clicks",
    )
    ip_hash = models.CharField(max_length=64, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    referrer = models.URLField(max_length=2000, blank=True)
    clicked_at = models.DateTimeField(auto_now_add=True, db_index=True)
    converted = models.BooleanField(default=False, db_index=True)

    class Meta:
        db_table = "analytics_linkclick"
        indexes = [
            models.Index(fields=["tracked_link", "clicked_at"]),
        ]

    def __str__(self):
        return f"Click({self.tracked_link.tracking_key} at {self.clicked_at})"


class KeywordRankHistory(models.Model):
    """Daily rank snapshot for a tracked keyword."""

    tracked_keyword = models.ForeignKey(
        TrackedKeyword, on_delete=models.CASCADE, related_name="history"
    )
    rank = models.IntegerField(null=True, blank=True)
    date = models.DateField(db_index=True)
    serp_features = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "analytics_keywordrankhistory"
        unique_together = [("tracked_keyword", "date")]
        ordering = ["-date"]

    def __str__(self):
        return f"Rank({self.tracked_keyword.keyword} #{self.rank} on {self.date})"


class KeywordScanConfig(TimestampMixin):
    """
    Per-website configuration for automatic DOM keyword scanning.
    Controls how frequently FetchBot re-scans the website's DOM to
    refresh keyword data and compare against tracked rankings.
    """

    INTERVAL_HOURLY = 1
    INTERVAL_6H = 6
    INTERVAL_DAILY = 24
    INTERVAL_WEEKLY = 168
    INTERVAL_CHOICES = [
        (INTERVAL_HOURLY, "Every hour"),
        (INTERVAL_6H, "Every 6 hours"),
        (INTERVAL_DAILY, "Daily"),
        (INTERVAL_WEEKLY, "Weekly"),
    ]

    website = models.OneToOneField(
        "websites.Website", on_delete=models.CASCADE, related_name="keyword_scan_config"
    )
    is_auto_scan_enabled = models.BooleanField(
        default=True, help_text="Automatically re-scan the DOM at the configured interval."
    )
    scan_interval_hours = models.IntegerField(
        default=INTERVAL_DAILY,
        help_text="How often to re-scan (in hours). Common values: 1, 6, 24, 168.",
    )
    scan_depth = models.IntegerField(
        default=5,
        help_text="Maximum number of pages to crawl per scan.",
    )
    last_scanned_at = models.DateTimeField(null=True, blank=True)
    next_scan_at = models.DateTimeField(null=True, blank=True)
    total_scans = models.IntegerField(default=0)

    class Meta:
        db_table = "analytics_keywordscanconfig"

    def __str__(self):
        return f"ScanConfig({self.website.name}, every {self.scan_interval_hours}h)"


class PlatformContent(TimestampMixin):
    """
    A piece of content (post, article, caption) from a social platform.
    Keywords are extracted from the content and compared against website keywords
    to surface gaps and opportunities.
    """

    PLATFORM_LINKEDIN = "linkedin"
    PLATFORM_X = "x"
    PLATFORM_FACEBOOK = "facebook"
    PLATFORM_INSTAGRAM = "instagram"
    PLATFORM_BLOG = "blog"
    PLATFORM_OTHER = "other"
    PLATFORM_CHOICES = [
        (PLATFORM_LINKEDIN, "LinkedIn"),
        (PLATFORM_X, "X (Twitter)"),
        (PLATFORM_FACEBOOK, "Facebook"),
        (PLATFORM_INSTAGRAM, "Instagram"),
        (PLATFORM_BLOG, "Blog / Article"),
        (PLATFORM_OTHER, "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    website = models.ForeignKey(
        "websites.Website", on_delete=models.CASCADE, related_name="platform_content"
    )
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, default=PLATFORM_LINKEDIN)
    title = models.CharField(max_length=300, blank=True, help_text="Post title or first line")
    content = models.TextField(help_text="Full text of the post or article")
    url = models.URLField(max_length=2000, blank=True, help_text="Link to the original post")
    published_at = models.DateTimeField(null=True, blank=True)

    # Keywords extracted from this content (populated automatically on save)
    extracted_keywords = models.JSONField(
        default=list,
        help_text='[{"keyword": "...", "density": 1.2, "count": 3}, ...]',
    )

    # Deduplication
    platform_post_id = models.CharField(
        max_length=300, blank=True, db_index=True,
        help_text="Platform-native post ID to prevent duplicates.",
    )

    class Meta:
        db_table = "analytics_platformcontent"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["website", "platform"]),
        ]

    def __str__(self):
        return f"PlatformContent({self.get_platform_display()}, {self.title[:60] or self.content[:60]})"

    def extract_keywords_from_content(self) -> list:
        """
        Simple keyword extraction from content text.
        Returns list of {"keyword": str, "count": int, "density": float}.
        """
        import re
        from collections import Counter

        text = f"{self.title} {self.content}".lower()
        words = re.findall(r"\b[a-z][a-z0-9\-]{2,}\b", text)

        stopwords = {
            "the", "and", "for", "are", "was", "were", "this", "that", "with",
            "have", "has", "had", "not", "but", "from", "they", "will", "can",
            "all", "our", "your", "their", "you", "its", "into", "out", "about",
            "been", "would", "could", "should", "also", "more", "some", "than",
            "when", "what", "how", "why", "who", "which", "just", "very", "here",
            "there", "each", "any", "one", "two", "three", "new", "get", "use",
        }
        words = [w for w in words if w not in stopwords and len(w) >= 3]

        word_count = len(words) or 1
        counts = Counter(words)
        return [
            {"keyword": w, "count": c, "density": round(c / word_count * 100, 2)}
            for w, c in counts.most_common(20)
        ]
