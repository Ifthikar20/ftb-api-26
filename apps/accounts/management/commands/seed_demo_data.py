"""
seed_demo_data — Populate all FetchBot models with realistic demo data.

Usage:  python manage.py seed_demo_data --settings=config.settings.dev
"""
import random
import uuid
from datetime import date, datetime, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Seeds the database with comprehensive demo data for all FetchBot modules."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding demo data..."))
        now = timezone.now()

        # ── Users ──
        from apps.accounts.models import User

        admin, _ = User.objects.get_or_create(
            email="admin@growthpilot.io",
            defaults={
                "full_name": "Admin User",
                "company_name": "GrowthPilot",
                "plan": "scale",
                "is_staff": True,
                "is_superuser": True,
                "is_email_verified": True,
            },
        )
        admin.set_password("AdminPass123!")
        admin.save()

        demo, _ = User.objects.get_or_create(
            email="demo@example.com",
            defaults={
                "full_name": "Demo User",
                "company_name": "Acme Corp",
                "plan": "growth",
                "is_email_verified": True,
            },
        )
        demo.set_password("DemoPass123!")
        demo.save()
        self.stdout.write(f"  Users: admin + demo")

        # ── Websites ──
        from apps.websites.models import Website, WebsiteSettings

        website, _ = Website.objects.get_or_create(
            user=demo,
            url="https://demo.example.com",
            defaults={"name": "Demo Website", "industry": "SaaS"},
        )
        WebsiteSettings.objects.get_or_create(website=website)
        self.stdout.write(f"  Website: {website.name} ({website.id})")

        # ── Visitors + Sessions + PageEvents ──
        from apps.analytics.models import Visitor, Session, PageEvent

        pages = [
            "/", "/features", "/pricing", "/blog", "/blog/growth-hacking-101",
            "/blog/seo-tips-2026", "/about", "/contact", "/demo", "/signup",
            "/case-studies", "/integrations", "/docs/api", "/changelog",
        ]
        sources = ["google", "direct", "twitter", "linkedin", "facebook", "referral", "email"]
        companies = [
            "TechCorp", "GreenLeaf Inc", "ByteWorks", "Pinnacle Solutions",
            "Horizon Media", "Quantum Labs", "NovaStar", "DataVault",
            "Silverline", "BlueShift", "CloudNine", "RedPeak",
        ]
        devices = ["desktop", "mobile", "tablet"]
        browsers = ["Chrome", "Firefox", "Safari", "Edge"]
        oses = ["Windows", "macOS", "iOS", "Android", "Linux"]

        visitors = []
        for i in range(50):
            v, _ = Visitor.objects.get_or_create(
                website=website,
                fingerprint_hash=f"fp_{i:04d}_{uuid.uuid4().hex[:8]}",
                defaults={
                    "company_name": random.choice(companies) if random.random() > 0.3 else "",
                    "geo_country": random.choice(["US", "GB", "CA", "DE", "AU", "FR", "IN"]),
                    "geo_city": random.choice(["New York", "London", "Toronto", "Berlin", "Sydney", "Paris"]),
                    "device_type": random.choice(devices),
                    "browser": random.choice(browsers),
                    "os": random.choice(oses),
                    "visit_count": random.randint(1, 15),
                    "lead_score": random.randint(0, 100),
                },
            )
            visitors.append(v)

        # Sessions and events
        for v in visitors[:30]:
            for j in range(random.randint(1, 4)):
                start = now - timedelta(days=random.randint(0, 30), hours=random.randint(0, 23))
                sess = Session.objects.create(
                    visitor=v,
                    started_at=start,
                    ended_at=start + timedelta(minutes=random.randint(1, 30)),
                    page_count=random.randint(1, 8),
                    entry_page=f"https://demo.example.com{random.choice(pages)}",
                    exit_page=f"https://demo.example.com{random.choice(pages)}",
                    source=random.choice(sources),
                    medium=random.choice(["organic", "cpc", "social", "referral", "email", ""]),
                )
                for _ in range(random.randint(1, 5)):
                    PageEvent.objects.create(
                        visitor=v,
                        website=website,
                        session=sess,
                        url=f"https://demo.example.com{random.choice(pages)}",
                        event_type=random.choice(["pageview", "click", "scroll", "form_submit"]),
                        timestamp=start + timedelta(minutes=random.randint(0, 20)),
                    )
        self.stdout.write(f"  Analytics: {len(visitors)} visitors, sessions, events")

        # ── Leads ──
        from apps.leads.models import Lead

        lead_data = [
            {"name": "Sarah Mitchell", "email": "sarah@techcorp.com", "company": "TechCorp", "score": 92, "status": "qualified", "source": "organic"},
            {"name": "James Lee", "email": "james@greenleaf.com", "company": "GreenLeaf Inc", "score": 87, "status": "contacted", "source": "referral"},
            {"name": "Emily Chen", "email": "emily@byteworks.io", "company": "ByteWorks", "score": 81, "status": "new", "source": "google"},
            {"name": "Robert Kim", "email": "robert@pinnacle.co", "company": "Pinnacle Solutions", "score": 78, "status": "qualified", "source": "linkedin"},
            {"name": "Maria Garcia", "email": "maria@horizon.media", "company": "Horizon Media", "score": 74, "status": "new", "source": "twitter"},
            {"name": "David Park", "email": "david@quantum.labs", "company": "Quantum Labs", "score": 68, "status": "contacted", "source": "organic"},
            {"name": "Lisa Wang", "email": "lisa@novastar.io", "company": "NovaStar", "score": 55, "status": "new", "source": "direct"},
            {"name": "Tom Harris", "email": "tom@datavault.com", "company": "DataVault", "score": 45, "status": "lost", "source": "email"},
            {"name": "Anna Brown", "email": "anna@silverline.co", "company": "Silverline", "score": 38, "status": "new", "source": "social"},
            {"name": "Chris Wright", "email": "chris@blueshift.dev", "company": "BlueShift", "score": 22, "status": "new", "source": "organic"},
            {"name": "Sophie Turner", "email": "sophie@cloudnine.io", "company": "CloudNine", "score": 91, "status": "customer", "source": "referral"},
            {"name": "Daniel Zhao", "email": "daniel@redpeak.com", "company": "RedPeak", "score": 85, "status": "qualified", "source": "google"},
        ]
        for i, ld in enumerate(lead_data):
            if i < len(visitors):
                Lead.objects.get_or_create(
                    visitor=visitors[i],
                    website=website,
                    defaults=ld,
                )
        self.stdout.write(f"  Leads: {len(lead_data)} created")

        # ── Competitors ──
        from apps.competitors.models import Competitor, CompetitorChange, KeywordGap

        comp_data = [
            {"name": "CompetitorX", "competitor_url": "https://competitorx.com", "estimated_traffic": 45000, "domain_authority": 62, "threat_level": "high"},
            {"name": "RivalCo", "competitor_url": "https://rivalco.io", "estimated_traffic": 28000, "domain_authority": 48, "threat_level": "medium"},
            {"name": "MarketPro", "competitor_url": "https://marketpro.com", "estimated_traffic": 65000, "domain_authority": 71, "threat_level": "critical"},
            {"name": "GrowthStack", "competitor_url": "https://growthstack.dev", "estimated_traffic": 12000, "domain_authority": 35, "threat_level": "low"},
        ]
        created_competitors = []
        for cd in comp_data:
            comp, _ = Competitor.objects.get_or_create(
                website=website,
                competitor_url=cd["competitor_url"],
                defaults=cd,
            )
            created_competitors.append(comp)

        changes = [
            {"change_type": "new_page", "detail": {"url": "/blog/growth-hacking", "title": "Growth Hacking Guide"}},
            {"change_type": "ranking_change", "detail": {"keyword": "marketing automation", "old_rank": 12, "new_rank": 5}},
            {"change_type": "content_update", "detail": {"url": "/pricing", "changes": "Added enterprise tier"}},
            {"change_type": "new_page", "detail": {"url": "/features/ai-assistant", "title": "AI Assistant Launch"}},
            {"change_type": "pricing_change", "detail": {"old_price": "$49/mo", "new_price": "$59/mo", "plan": "Pro"}},
        ]
        for i, ch in enumerate(changes):
            CompetitorChange.objects.get_or_create(
                competitor=created_competitors[i % len(created_competitors)],
                change_type=ch["change_type"],
                detected_at=now - timedelta(days=i, hours=random.randint(0, 12)),
                defaults={"detail": ch["detail"]},
            )

        gap_keywords = [
            {"keyword": "growth hacking tools", "your_rank": None, "search_volume": 8200, "difficulty": 45, "opportunity_score": 0.85},
            {"keyword": "marketing automation", "your_rank": 18, "search_volume": 22000, "difficulty": 72, "opportunity_score": 0.6},
            {"keyword": "seo audit tool", "your_rank": 8, "search_volume": 14000, "difficulty": 58, "opportunity_score": 0.72},
            {"keyword": "competitor analysis", "your_rank": 25, "search_volume": 9800, "difficulty": 52, "opportunity_score": 0.78},
            {"keyword": "lead scoring software", "your_rank": None, "search_volume": 5400, "difficulty": 38, "opportunity_score": 0.9},
            {"keyword": "website analytics", "your_rank": 14, "search_volume": 33000, "difficulty": 82, "opportunity_score": 0.5},
        ]
        for gk in gap_keywords:
            comp_ranks = {c.name: random.randint(1, 20) for c in created_competitors[:3]}
            KeywordGap.objects.get_or_create(
                website=website,
                keyword=gk["keyword"],
                defaults={**gk, "competitor_ranks": comp_ranks},
            )
        self.stdout.write(f"  Competitors: {len(comp_data)} + {len(changes)} changes + {len(gap_keywords)} keyword gaps")

        # ── Audits ──
        from apps.audits.models import Audit, AuditIssue

        audit1, _ = Audit.objects.get_or_create(
            website=website,
            status="completed",
            overall_score=78,
            defaults={
                "triggered_by": demo,
                "completed_at": now - timedelta(hours=2),
                "seo_score": 82,
                "performance_score": 71,
                "mobile_score": 85,
                "security_score": 90,
                "content_score": 65,
            },
        )
        audit2, _ = Audit.objects.get_or_create(
            website=website,
            status="completed",
            overall_score=72,
            defaults={
                "triggered_by": demo,
                "completed_at": now - timedelta(days=7),
                "seo_score": 75,
                "performance_score": 68,
                "mobile_score": 80,
                "security_score": 88,
                "content_score": 60,
            },
        )

        issues = [
            {"category": "seo", "severity": "critical", "title": "Missing meta descriptions on 5 pages", "description": "Pages without meta descriptions may rank lower in search.", "recommendation": "Add unique meta descriptions to /pricing, /features, /about, /blog, /demo", "impact_score": 90},
            {"category": "performance", "severity": "warning", "title": "Large uncompressed images", "description": "3 images over 500KB detected on homepage.", "recommendation": "Compress images using WebP format and lazy-load below-the-fold images.", "impact_score": 75},
            {"category": "seo", "severity": "warning", "title": "Duplicate H1 tags on 2 pages", "description": "Multiple H1 elements confuse search engines.", "recommendation": "Ensure each page has a single, unique H1 tag.", "impact_score": 65},
            {"category": "security", "severity": "info", "title": "Content Security Policy not configured", "description": "CSP headers help prevent XSS attacks.", "recommendation": "Add Content-Security-Policy header via your web server config.", "impact_score": 40},
            {"category": "mobile", "severity": "warning", "title": "Touch targets too small", "description": "3 buttons have touch targets under 48x48px.", "recommendation": "Increase button padding to meet minimum tap target size.", "impact_score": 55},
            {"category": "performance", "severity": "critical", "title": "Render-blocking JavaScript", "description": "2 scripts block page rendering for 1.2s.", "recommendation": "Add async/defer attributes to non-critical scripts.", "impact_score": 85},
            {"category": "content", "severity": "warning", "title": "Thin content on 3 pages", "description": "Pages with under 300 words score lower for SEO.", "recommendation": "Expand content on /features, /integrations, /changelog.", "impact_score": 50},
        ]
        for issue in issues:
            AuditIssue.objects.get_or_create(
                audit=audit1,
                title=issue["title"],
                defaults=issue,
            )
        self.stdout.write(f"  Audits: 2 completed + {len(issues)} issues")

        # ── Strategy ──
        from apps.strategy.models import Strategy, Action, ContentCalendarEntry, MorningBrief

        strategy, _ = Strategy.objects.get_or_create(
            website=website,
            status="active",
            defaults={
                "plan_type": "30",
                "completion_pct": 43,
                "summary": "Focus on SEO quick wins, content expansion, and competitor gap analysis. Primary goal: increase organic traffic by 20% in 30 days.",
            },
        )

        actions_data = [
            {"title": "Publish blog post on SEO Trends 2026", "description": "Write and publish a 2000-word article covering the latest SEO trends.", "action_type": "content", "estimated_impact": "high", "status": "done", "week_number": 1},
            {"title": "Review competitor keyword gaps", "description": "Analyze keyword gaps with top 3 competitors and identify opportunities.", "action_type": "research", "estimated_impact": "medium", "status": "done", "week_number": 1},
            {"title": "Update meta descriptions on top 5 pages", "description": "Rewrite meta descriptions for pages with highest traffic potential.", "action_type": "seo", "estimated_impact": "high", "status": "done", "week_number": 1},
            {"title": "Set up lead scoring for new funnel", "description": "Configure scoring rules for the new product demo funnel.", "action_type": "leads", "estimated_impact": "medium", "status": "todo", "week_number": 2},
            {"title": "Create social media calendar for April", "description": "Plan 12 social posts across LinkedIn and Twitter.", "action_type": "content", "estimated_impact": "low", "status": "todo", "week_number": 2},
            {"title": "Respond to hot lead from TechCorp", "description": "Follow up with Sarah Mitchell who has a lead score of 92.", "action_type": "outreach", "estimated_impact": "high", "status": "todo", "week_number": 2},
            {"title": "Share weekly report with team", "description": "Compile this week metrics and share via email.", "action_type": "reporting", "estimated_impact": "low", "status": "todo", "week_number": 2},
        ]
        for ad in actions_data:
            Action.objects.get_or_create(
                strategy=strategy,
                title=ad["title"],
                defaults={**ad, "due_date": date.today() + timedelta(days=ad["week_number"] * 7)},
            )

        cal_entries = [
            {"title": "SEO Trends 2026 Blog Post", "topic": "SEO", "content_type": "blog", "scheduled_date": date.today() + timedelta(days=2)},
            {"title": "LinkedIn post: Growth Tips", "topic": "Growth", "content_type": "social", "scheduled_date": date.today() + timedelta(days=3)},
            {"title": "Weekly Newsletter", "topic": "Recap", "content_type": "email", "scheduled_date": date.today() + timedelta(days=5)},
            {"title": "How-to video: Lead Scoring", "topic": "Product", "content_type": "video", "scheduled_date": date.today() + timedelta(days=8)},
            {"title": "Competitor Analysis Report", "topic": "Strategy", "content_type": "blog", "scheduled_date": date.today() + timedelta(days=10)},
        ]
        for ce in cal_entries:
            ContentCalendarEntry.objects.get_or_create(
                website=website,
                title=ce["title"],
                defaults=ce,
            )

        MorningBrief.objects.get_or_create(
            website=website,
            date=date.today(),
            defaults={
                "content": "Your website traffic is up 12% compared to last week. Three new hot leads were identified overnight from organic search. Your competitor CompetitorX published 2 new blog posts. Consider running your weekly audit to check for SEO improvements.",
                "metrics_snapshot": {
                    "visitors_today": 847,
                    "visitors_change": 12.5,
                    "hot_leads": 38,
                    "growth_score": 74,
                    "conversion_rate": 3.2,
                },
            },
        )
        self.stdout.write(f"  Strategy: active + {len(actions_data)} actions + {len(cal_entries)} calendar + brief")

        # ── Notifications ──
        from apps.notifications.models import Notification

        notif_data = [
            {"type": "hot_lead", "title": "New Hot Lead", "message": "Sarah Mitchell from TechCorp just scored 92. Time to reach out.", "action_url": "/leads"},
            {"type": "audit_complete", "title": "Audit Complete", "message": "Your website audit is done. Overall score: 78/100.", "action_url": "/audits"},
            {"type": "competitor_alert", "title": "Competitor Alert", "message": "CompetitorX is now ranking for 'growth hacking tools'.", "action_url": "/competitors"},
            {"type": "strategy", "title": "Strategy Updated", "message": "3 new action items generated for this week.", "action_url": "/strategy"},
            {"type": "milestone", "title": "Traffic Milestone", "message": "You hit 10,000 monthly visitors for the first time.", "action_url": "/analytics"},
        ]
        for nd in notif_data:
            Notification.objects.get_or_create(
                user=demo,
                title=nd["title"],
                defaults=nd,
            )
        self.stdout.write(f"  Notifications: {len(notif_data)}")

        # ── Billing ──
        from apps.billing.models import Subscription, Invoice, UsageRecord

        sub, _ = Subscription.objects.get_or_create(
            user=demo,
            defaults={
                "stripe_customer_id": f"cus_demo_{uuid.uuid4().hex[:8]}",
                "stripe_subscription_id": f"sub_demo_{uuid.uuid4().hex[:8]}",
                "plan": "growth",
                "status": "active",
                "current_period_start": now - timedelta(days=15),
                "current_period_end": now + timedelta(days=15),
            },
        )

        for i in range(3):
            Invoice.objects.get_or_create(
                subscription=sub,
                stripe_invoice_id=f"inv_demo_{i}_{uuid.uuid4().hex[:6]}",
                defaults={
                    "amount_paid": 4900,
                    "currency": "usd",
                    "status": "paid",
                    "period_start": now - timedelta(days=30 * (i + 1)),
                    "period_end": now - timedelta(days=30 * i),
                },
            )

        usage_metrics = [
            {"metric": "pageviews", "count": 24500},
            {"metric": "audits", "count": 8},
            {"metric": "ai_calls", "count": 45},
            {"metric": "leads", "count": 127},
        ]
        for um in usage_metrics:
            UsageRecord.objects.get_or_create(
                subscription=sub,
                metric=um["metric"],
                period_start=date.today().replace(day=1),
                defaults={
                    "count": um["count"],
                    "period_end": (date.today().replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1),
                },
            )
        self.stdout.write(f"  Billing: subscription + 3 invoices + {len(usage_metrics)} usage records")

        self.stdout.write(self.style.SUCCESS("Done. All demo data seeded."))
