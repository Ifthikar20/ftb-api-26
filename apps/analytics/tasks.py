import logging

from celery import shared_task

logger = logging.getLogger("apps")


@shared_task(name="apps.analytics.tasks.aggregate_hourly_metrics")
def aggregate_hourly_metrics():
    """Pre-aggregate hourly analytics data."""
    from apps.analytics.services.aggregation_service import AggregationService
    from apps.websites.models import Website

    for website in Website.objects.filter(is_active=True):
        try:
            AggregationService.aggregate_hourly(website_id=str(website.id))
        except Exception as e:
            logger.error(f"Aggregation failed for website {website.id}: {e}")


@shared_task(name="apps.analytics.tasks.check_keyword_alerts")
def check_keyword_alerts():
    """
    Runs on a schedule (e.g. every hour via celery-beat).
    For every active KeywordAlert, checks whether the associated keyword(s)
    have moved enough positions to trigger the alert.
    """
    from django.utils import timezone

    from apps.analytics.models import KeywordAlert, KeywordAlertEvent, TrackedKeyword

    for alert in KeywordAlert.objects.filter(is_active=True).select_related("tracked_keyword", "website", "website__user"):
        if alert.tracked_keyword:
            keywords = [alert.tracked_keyword]
        else:
            keywords = list(TrackedKeyword.objects.filter(website=alert.website))

        for kw in keywords:
            if kw.current_rank is None or kw.previous_rank is None:
                continue
            # Positive change = rank number went DOWN = improved position
            change = kw.previous_rank - kw.current_rank
            abs_change = abs(change)
            if abs_change < alert.threshold:
                continue
            if alert.direction == KeywordAlert.DIRECTION_IMPROVED and change <= 0:
                continue
            if alert.direction == KeywordAlert.DIRECTION_DECLINED and change >= 0:
                continue

            # Create the event record
            event = KeywordAlertEvent.objects.create(
                alert=alert,
                keyword=kw.keyword,
                old_rank=kw.previous_rank,
                new_rank=kw.current_rank,
                change=change,
            )
            alert.last_triggered_at = timezone.now()
            alert.save(update_fields=["last_triggered_at"])

            if alert.notification_method == KeywordAlert.METHOD_EMAIL:
                _send_keyword_alert_email(alert, event)

            logger.info(
                f"Keyword alert fired: '{kw.keyword}' moved {abs_change} positions "
                f"({'up' if change > 0 else 'down'}) for website {alert.website_id}"
            )


def _send_keyword_alert_email(alert, event):
    """Send an email notification for a triggered keyword alert."""
    try:
        from django.conf import settings
        from django.core.mail import send_mail

        user = alert.website.user
        direction = "improved" if event.change > 0 else "declined"
        subject = f"Keyword alert: '{event.keyword}' {direction} {abs(event.change)} positions"
        body = (
            f"Hi,\n\n"
            f"Your keyword tracking alert has fired.\n\n"
            f"Keyword: {event.keyword}\n"
            f"Change: {abs(event.change)} positions {direction}\n"
            f"Old rank: #{event.old_rank}\n"
            f"New rank: #{event.new_rank}\n\n"
            f"Log in to your dashboard to see the full report.\n"
        )
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )
    except Exception as e:
        logger.warning(f"Failed to send keyword alert email: {e}")


@shared_task(name="apps.analytics.tasks.check_competitor_rankings")
def check_competitor_rankings(competitor_id: str):
    """
    Fetch DataForSEO rankings for a single competitor domain across
    all tracked keywords for its parent website.
    """
    from django.utils import timezone

    from apps.analytics.models import CompetitorDomain, CompetitorKeywordRank, TrackedKeyword
    from apps.analytics.services.dataforseo_service import DataForSEOService

    try:
        comp = CompetitorDomain.objects.select_related("website").get(id=competitor_id)
    except CompetitorDomain.DoesNotExist:
        logger.warning(f"Competitor {competitor_id} not found")
        return

    if not DataForSEOService.is_configured():
        logger.warning("DataForSEO not configured — skipping competitor rank check")
        return

    keywords = list(
        TrackedKeyword.objects.filter(website=comp.website).values_list("keyword", flat=True)
    )
    if not keywords:
        return

    try:
        enriched = DataForSEOService.enrich_keywords(keywords, comp.domain)
        for entry in enriched:
            CompetitorKeywordRank.objects.create(
                competitor=comp,
                keyword=entry["keyword"],
                rank=entry.get("position"),
            )
        comp.last_checked_at = timezone.now()
        comp.save(update_fields=["last_checked_at"])
        logger.info(f"Competitor ranks updated for {comp.domain}: {len(enriched)} keywords")
    except Exception as e:
        logger.error(f"Competitor rank check failed for {comp.domain}: {e}")


# ── Auto Keyword Scan ────────────────────────────────────────────────────────


@shared_task(name="apps.analytics.tasks.run_auto_keyword_scans")
def run_auto_keyword_scans():
    """Celery-beat dispatcher: check all KeywordScanConfigs and queue scans
    for websites that are due.

    Runs every 15 minutes. For each config where ``is_auto_scan_enabled``
    is True and ``next_scan_at <= now`` (or next_scan_at is null), we
    dispatch ``execute_keyword_scan`` on the ``ai`` queue.
    """
    from django.utils import timezone as tz

    from apps.analytics.models import KeywordScanConfig

    now = tz.now()
    due = KeywordScanConfig.objects.filter(
        is_auto_scan_enabled=True,
    ).select_related("website").filter(
        # next_scan_at is null (never scanned) OR overdue
        models_q_or(next_scan_at__isnull=True, next_scan_at__lte=now),
    )

    count = 0
    for config in due:
        execute_keyword_scan.delay(str(config.website_id))
        count += 1

    if count:
        logger.info(f"auto_keyword_scans: dispatched {count} scan(s)")


def models_q_or(**kwargs):
    """Build a Q(a=1) | Q(b=2) filter from kwargs."""
    from django.db.models import Q
    combined = Q()
    for k, v in kwargs.items():
        combined |= Q(**{k: v})
    return combined


@shared_task(
    name="apps.analytics.tasks.execute_keyword_scan",
    bind=True,
    max_retries=2,
    default_retry_delay=120,
)
def execute_keyword_scan(self, website_id: str):
    """Execute a full keyword scan for one website.

    1. Crawl the site with SEOKeywordScanner
    2. Auto-create/update TrackedKeyword rows
    3. Record KeywordRankHistory snapshots
    4. Enrich with DataForSEO if configured
    5. Stamp last_scanned_at and compute next_scan_at
    """
    import hashlib
    from datetime import timedelta
    from urllib.parse import urlparse

    from django.core.cache import cache
    from django.utils import timezone as tz

    from apps.analytics.models import (
        KeywordRankHistory,
        KeywordScanConfig,
        TrackedKeyword,
    )
    from apps.analytics.services.seo_keyword_scanner import SEOKeywordScanner
    from apps.websites.models import Website

    try:
        website = Website.objects.get(id=website_id)
    except Website.DoesNotExist:
        logger.warning(f"execute_keyword_scan: website {website_id} not found")
        return

    config, _ = KeywordScanConfig.objects.get_or_create(website=website)

    logger.info(f"keyword_scan_start: {website.name} ({website.url})")

    # Clear scan cache to force fresh crawl
    cache_key = f"seo_scan_{hashlib.md5(website.url.encode()).hexdigest()}"
    cache.delete(cache_key)

    # 1. Run the full scan
    result = SEOKeywordScanner.scan(
        website_url=website.url,
        website_id=str(website.id),
    )
    if result.get("error"):
        logger.error(f"keyword_scan_failed: {website.name} — {result['error']}")
        return

    # 2. Upsert TrackedKeyword rows from scan results
    trends = result.get("trends", {})
    today = tz.now().date()
    keywords_updated = 0

    for kw_data in result.get("keywords", [])[:15]:
        kw_text = kw_data["keyword"]
        trend_info = trends.get(kw_text, {})
        interest = trend_info.get("interest", 0)

        tk, created = TrackedKeyword.objects.get_or_create(
            website_id=website_id,
            keyword=kw_text,
            defaults={
                "target_url": website.url,
                "search_volume": interest * 100,
                "difficulty": min(100, max(0, round(kw_data.get("density", 0) * 25))),
            },
        )

        # 3. Record daily rank history (one entry per keyword per day)
        KeywordRankHistory.objects.update_or_create(
            tracked_keyword=tk,
            date=today,
            defaults={
                "rank": tk.current_rank,
                "serp_features": [],
            },
        )
        keywords_updated += 1

    # 4. DataForSEO enrichment (optional — only if credentials are set)
    try:
        from apps.analytics.services.dataforseo_service import DataForSEOService

        if DataForSEOService.is_configured():
            domain = urlparse(website.url).netloc.replace("www.", "")
            kw_list = [k["keyword"] for k in result.get("keywords", [])[:12]]
            enriched = DataForSEOService.enrich_keywords(kw_list, domain)

            for e in enriched:
                if not e.get("enriched"):
                    continue
                tk = TrackedKeyword.objects.filter(
                    website_id=website_id,
                    keyword=e["keyword"],
                ).first()
                if not tk:
                    continue

                changed = []
                if e.get("volume"):
                    tk.search_volume = e["volume"]
                    changed.append("search_volume")
                if e.get("difficulty"):
                    tk.difficulty = e["difficulty"]
                    changed.append("difficulty")
                if e.get("position"):
                    if tk.current_rank is not None:
                        tk.previous_rank = tk.current_rank
                        changed.append("previous_rank")
                    tk.current_rank = e["position"]
                    changed.append("current_rank")
                    if not tk.best_rank or e["position"] < tk.best_rank:
                        tk.best_rank = e["position"]
                        changed.append("best_rank")
                if changed:
                    tk.save(update_fields=changed)

                # Update today's history with real rank
                if e.get("position"):
                    KeywordRankHistory.objects.update_or_create(
                        tracked_keyword=tk,
                        date=today,
                        defaults={
                            "rank": e["position"],
                            "serp_features": e.get("serp_features", []),
                        },
                    )
    except Exception as exc:
        logger.warning(f"DataForSEO enrichment skipped: {exc}")

    # 5. Update scan config timestamps
    now = tz.now()
    config.last_scanned_at = now
    config.next_scan_at = now + timedelta(hours=config.scan_interval_hours)
    config.total_scans += 1
    config.save(update_fields=["last_scanned_at", "next_scan_at", "total_scans"])

    logger.info(
        f"keyword_scan_complete: {website.name} — "
        f"{keywords_updated} keywords, score={result.get('score', 0)}, "
        f"next scan at {config.next_scan_at.isoformat()}"
    )


# ── Platform Trend Fetcher ───────────────────────────────────────────────────


@shared_task(name="apps.analytics.tasks.fetch_platform_trends")
def fetch_platform_trends():
    """Fetch trending topics from X (Twitter) and Google Trends and store
    them as PlatformContent for every website that has auto-scan enabled.

    This allows keyword gap analysis to compare site keywords against
    what's trending on social platforms right now.
    """
    from django.utils import timezone as tz

    from apps.analytics.models import KeywordScanConfig, PlatformContent

    configs = KeywordScanConfig.objects.filter(
        is_auto_scan_enabled=True
    ).select_related("website")

    if not configs.exists():
        return

    # ── 1. Fetch X (Twitter) trends ──
    x_trends = _fetch_x_trends()

    # ── 2. Fetch Google Trends ──
    google_trends = _fetch_google_trends()

    now = tz.now()
    created_count = 0

    for config in configs:
        website = config.website

        # Store X trends as PlatformContent (deduplicated by date)
        for trend in x_trends:
            post_id = f"x_trend_{now.strftime('%Y%m%d')}_{trend['name'][:60]}"
            _, created = PlatformContent.objects.get_or_create(
                website=website,
                platform_post_id=post_id,
                defaults={
                    "platform": PlatformContent.PLATFORM_X,
                    "title": trend["name"],
                    "content": trend.get("description", trend["name"]),
                    "url": trend.get("url", ""),
                    "published_at": now,
                },
            )
            if created:
                # Extract keywords from the trend content
                obj = PlatformContent.objects.get(
                    website=website, platform_post_id=post_id
                )
                obj.extracted_keywords = obj.extract_keywords_from_content()
                obj.save(update_fields=["extracted_keywords"])
                created_count += 1

        # Store Google Trends as PlatformContent
        for kw in google_trends:
            post_id = f"gtrend_{now.strftime('%Y%m%d')}_{kw[:60]}"
            _, created = PlatformContent.objects.get_or_create(
                website=website,
                platform_post_id=post_id,
                defaults={
                    "platform": PlatformContent.PLATFORM_OTHER,
                    "title": f"Google Trend: {kw}",
                    "content": kw,
                    "published_at": now,
                },
            )
            if created:
                obj = PlatformContent.objects.get(
                    website=website, platform_post_id=post_id
                )
                obj.extracted_keywords = obj.extract_keywords_from_content()
                obj.save(update_fields=["extracted_keywords"])
                created_count += 1

    if created_count:
        logger.info(f"platform_trends: stored {created_count} new trend posts")


def _fetch_x_trends() -> list:
    """Fetch trending topics from X (Twitter) using the free v2 API.

    Requires ``X_BEARER_TOKEN`` in settings. If not configured, returns
    an empty list (graceful degradation).

    Returns list of dicts: [{"name": ..., "tweet_volume": ..., "url": ...}]
    """
    from django.conf import settings
    from django.core.cache import cache

    cache_key = "x_trends_us"
    cached = cache.get(cache_key)
    if cached:
        return cached

    bearer = getattr(settings, "X_BEARER_TOKEN", "")
    if not bearer:
        logger.info("X_BEARER_TOKEN not set — skipping X trends")
        return []

    try:
        import requests

        # WOEID 23424977 = United States
        resp = requests.get(
            "https://api.x.com/1.1/trends/place.json",
            params={"id": "23424977"},
            headers={"Authorization": f"Bearer {bearer}"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        trends = []
        if data and isinstance(data, list) and data[0].get("trends"):
            for t in data[0]["trends"][:20]:
                trends.append({
                    "name": t.get("name", ""),
                    "tweet_volume": t.get("tweet_volume"),
                    "url": t.get("url", ""),
                    "description": t.get("name", ""),
                })

        cache.set(cache_key, trends, 1800)  # Cache 30 min
        return trends

    except ImportError:
        logger.warning("requests not installed for X trends")
        return []
    except Exception as e:
        logger.warning(f"X trends fetch failed: {e}")
        return []


def _fetch_google_trends() -> list:
    """Fetch today's trending searches from Google Trends.

    Returns a simple list of keyword strings.
    """
    from django.core.cache import cache

    cache_key = "google_daily_trends"
    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl="en-US", tz=360, timeout=(10, 25))
        trending = pytrends.trending_searches(pn="united_states")
        keywords = [str(kw) for kw in trending[0].tolist()[:15]]
        cache.set(cache_key, keywords, 1800)
        return keywords

    except ImportError:
        logger.info("pytrends not installed — skipping Google Trends")
        return []
    except Exception as e:
        logger.warning(f"Google Trends fetch failed: {e}")
        return []

