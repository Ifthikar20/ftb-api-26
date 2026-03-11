"""Seed analytics data for a specific website."""
import random
import uuid
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Seed analytics, heatmap, and lead data for a specific website."

    def add_arguments(self, parser):
        parser.add_argument("--website-id", required=True)

    def handle(self, *args, **options):
        from apps.analytics.models import Visitor, Session, PageEvent
        from apps.leads.models import Lead
        from apps.websites.models import Website

        wid = options["website_id"]
        now = timezone.now()
        website = Website.objects.get(id=wid)
        self.stdout.write(f"Seeding for: {website.name} (owner: {website.user.email})")

        pages = ["/", "/features", "/pricing", "/blog", "/about", "/contact", "/demo", "/signup"]
        sources = ["google", "direct", "twitter", "linkedin", "facebook", "referral"]
        companies = ["TechCorp", "GreenLeaf Inc", "ByteWorks", "Pinnacle Solutions",
                      "Horizon Media", "Quantum Labs", "NovaStar", "DataVault",
                      "Silverline", "BlueShift"]
        devices = ["desktop", "mobile", "tablet"]
        browsers = ["Chrome", "Firefox", "Safari", "Edge"]

        # 1. Visitors (bulk)
        vs = []
        for i in range(50):
            vs.append(Visitor(
                website=website,
                fingerprint_hash=f"v3_{i:04d}_{uuid.uuid4().hex[:6]}",
                company_name=random.choice(companies) if random.random() > 0.3 else "",
                geo_country=random.choice(["US", "GB", "CA", "DE", "AU"]),
                geo_city=random.choice(["New York", "London", "Toronto", "Berlin", "Sydney"]),
                device_type=random.choice(devices),
                browser=random.choice(browsers),
                os=random.choice(["Windows", "macOS", "iOS", "Android"]),
                visit_count=random.randint(1, 15),
                lead_score=random.randint(0, 100),
            ))
        visitors = Visitor.objects.bulk_create(vs)
        self.stdout.write(f"  Visitors: {len(visitors)}")

        # 2. Sessions + Events (bulk)
        sessions_objs = []
        for v in visitors[:30]:
            for _ in range(random.randint(1, 3)):
                start = now - timedelta(days=random.randint(0, 30), hours=random.randint(0, 23))
                sessions_objs.append(Session(
                    visitor=v, started_at=start,
                    ended_at=start + timedelta(minutes=random.randint(1, 30)),
                    page_count=random.randint(1, 8),
                    entry_page=f"https://fetchbot.ai{random.choice(pages)}",
                    exit_page=f"https://fetchbot.ai{random.choice(pages)}",
                    source=random.choice(sources),
                ))
        created_sessions = Session.objects.bulk_create(sessions_objs)

        events = []
        for sess in created_sessions:
            for _ in range(random.randint(1, 4)):
                events.append(PageEvent(
                    visitor=sess.visitor, website=website, session=sess,
                    url=f"https://fetchbot.ai{random.choice(pages)}",
                    event_type=random.choice(["pageview", "click", "scroll", "form_submit"]),
                    timestamp=sess.started_at + timedelta(minutes=random.randint(0, 15)),
                ))
        PageEvent.objects.bulk_create(events)
        self.stdout.write(f"  Sessions: {len(created_sessions)}, Events: {len(events)}")

        # 3. Heatmap clicks (bulk)
        clicks = []
        zones = [
            ((5, 95), (1, 5), 30), ((30, 70), (25, 35), 40),
            ((10, 90), (45, 60), 25), ((15, 85), (65, 80), 20),
            ((5, 95), (90, 98), 10), ((1, 10), (10, 90), 15),
        ]
        for page in ["/", "/pricing", "/features", "/blog"]:
            for (xr, yr, w) in zones:
                for _ in range(w):
                    x = max(0, min(100, random.uniform(*xr) + random.gauss(0, 3)))
                    y = max(0, min(100, random.uniform(*yr) + random.gauss(0, 2)))
                    clicks.append(PageEvent(
                        visitor=random.choice(visitors[:20]), website=website,
                        url=f"https://fetchbot.ai{page}", event_type="click",
                        properties={"x_pct": round(x, 1), "y_pct": round(y, 1), "selector": "button.cta"},
                        timestamp=now - timedelta(days=random.randint(0, 30), hours=random.randint(0, 23)),
                    ))
        PageEvent.objects.bulk_create(clicks)
        self.stdout.write(f"  Heatmap clicks: {len(clicks)}")

        # 4. Leads (bulk)
        lead_info = [
            ("Sarah Mitchell", "sarah@techcorp.com", "TechCorp", 92, "qualified"),
            ("James Lee", "james@greenleaf.com", "GreenLeaf Inc", 87, "contacted"),
            ("Emily Chen", "emily@byteworks.io", "ByteWorks", 81, "new"),
            ("Robert Kim", "robert@pinnacle.co", "Pinnacle Solutions", 78, "qualified"),
            ("Maria Garcia", "maria@horizon.media", "Horizon Media", 74, "new"),
            ("David Park", "david@quantum.labs", "Quantum Labs", 68, "contacted"),
            ("Lisa Wang", "lisa@novastar.io", "NovaStar", 55, "new"),
            ("Tom Harris", "tom@datavault.com", "DataVault", 45, "lost"),
            ("Anna Brown", "anna@silverline.co", "Silverline", 38, "new"),
            ("Chris Wright", "chris@blueshift.dev", "BlueShift", 22, "new"),
            ("Sophie Turner", "sophie@cloudnine.io", "CloudNine", 91, "customer"),
            ("Daniel Zhao", "daniel@redpeak.com", "RedPeak", 85, "qualified"),
        ]
        lds = []
        for i, (name, email, co, score, status) in enumerate(lead_info):
            if i < len(visitors):
                lds.append(Lead(
                    visitor=visitors[i], website=website,
                    name=name, email=email, company=co, score=score, status=status, source="organic",
                ))
        Lead.objects.bulk_create(lds, ignore_conflicts=True)
        self.stdout.write(f"  Leads: {len(lds)}")

        # Flush Redis
        try:
            from django.core.cache import cache
            cache.clear()
        except Exception:
            pass

        self.stdout.write(self.style.SUCCESS("Done! All data seeded."))
