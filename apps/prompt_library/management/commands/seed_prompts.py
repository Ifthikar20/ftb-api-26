"""Seed the prompt library with curated real-world prompts.

These are hand-written to mirror the kind of question real users ask AI
assistants in each broad industry. They are *not* generated dummy data —
they're representative of Reddit threads, "best X for Y" search patterns,
"X vs Y" comparisons, and "near me" / local intent. Sources are marked
``manual`` so a future miner run can layer Reddit / SerpAPI rows on top
without colliding (text_hash dedup applies).

Run with:
    python manage.py seed_prompts            # idempotent, upserts
    python manage.py seed_prompts --reset    # delete manual rows first
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.prompt_library.models import (
    Industry,
    IntentBucket,
    Prompt,
    PromptSource,
)
from apps.prompt_library.services._hash import text_hash

# Demand score is a 0..1 popularity proxy. We bucket: 0.85+ = very hot,
# 0.6 = strong, 0.4 = mid, 0.25 = niche/long-tail. Numbers are heuristic
# and meant to give the UI a defensible default ordering until real
# mining replaces them.
SEED: dict[str, dict[str, list[tuple[str, float]]]] = {
    "saas-crm": {
        "category": [
            ("best CRM for small teams 2025", 0.92),
            ("free CRM with email sequences", 0.78),
            ("simple CRM for solo founders", 0.7),
            ("crm for real estate agents", 0.66),
            ("best CRM for startups under 10 people", 0.74),
        ],
        "comparison": [
            ("HubSpot vs Salesforce for small business", 0.9),
            ("Pipedrive vs Close CRM", 0.7),
            ("Attio vs HubSpot for B2B", 0.62),
            ("Salesforce vs Zoho CRM pricing", 0.6),
        ],
        "problem": [
            ("how to import contacts from Google into HubSpot", 0.55),
            ("CRM keeps duplicating leads from Zapier", 0.5),
            ("how to track inbound email replies in CRM", 0.58),
            ("best way to sync CRM with Gmail", 0.6),
        ],
        "local": [
            ("CRM consultants near me", 0.32),
            ("HubSpot certified partners NYC", 0.28),
            ("Salesforce implementation Chicago", 0.3),
        ],
    },
    "saas-analytics": {
        "category": [
            ("best product analytics tool for early stage", 0.85),
            ("open source web analytics tools", 0.75),
            ("alternatives to Google Analytics 4", 0.88),
            ("event tracking platform for mobile apps", 0.65),
        ],
        "comparison": [
            ("Mixpanel vs Amplitude 2025", 0.92),
            ("PostHog vs Mixpanel", 0.78),
            ("GA4 vs Plausible vs Fathom", 0.72),
            ("Heap vs Pendo for SaaS", 0.55),
        ],
        "problem": [
            ("how to track funnel drop-off without engineering", 0.6),
            ("Mixpanel events not firing on Safari", 0.5),
            ("attribution across web and mobile", 0.65),
            ("how to deduplicate users across devices", 0.55),
        ],
        "local": [
            ("data analytics consultants London", 0.3),
            ("analytics implementation agency Bay Area", 0.28),
        ],
    },
    "saas-devtools": {
        "category": [
            ("best CI/CD platform for monorepos", 0.78),
            ("feature flag tools for small teams", 0.7),
            ("error monitoring tools for Node.js", 0.72),
            ("best secrets manager for kubernetes", 0.62),
        ],
        "comparison": [
            ("GitHub Actions vs CircleCI vs Buildkite", 0.85),
            ("LaunchDarkly vs Statsig vs Flagsmith", 0.7),
            ("Sentry vs Datadog APM", 0.8),
            ("Vercel vs Netlify vs Cloudflare Pages", 0.88),
        ],
        "problem": [
            ("CI build is slow on monorepo with pnpm", 0.55),
            ("how to roll back a feature flag without redeploy", 0.5),
            ("Sentry source maps not uploading on Vercel", 0.45),
            ("how to manage env vars across environments safely", 0.62),
        ],
        "local": [
            ("DevOps consultants Berlin", 0.3),
            ("kubernetes contractors Austin", 0.28),
        ],
    },
    "e-commerce-dtc": {
        "category": [
            ("best Shopify apps for upsells 2025", 0.88),
            ("subscription billing for DTC brands", 0.7),
            ("headless commerce platforms", 0.68),
            ("best email marketing for ecommerce", 0.85),
        ],
        "comparison": [
            ("Shopify vs WooCommerce 2025", 0.92),
            ("Klaviyo vs Mailchimp for ecommerce", 0.85),
            ("Recharge vs Stay Ai vs Skio", 0.6),
            ("BigCommerce vs Shopify Plus", 0.58),
        ],
        "problem": [
            ("how to reduce cart abandonment on Shopify", 0.78),
            ("klaviyo flow not sending after checkout", 0.45),
            ("how to set up upsell after purchase", 0.62),
            ("how to handle international shipping rates", 0.55),
        ],
        "local": [
            ("Shopify agency near me", 0.4),
            ("ecommerce photographer Los Angeles", 0.32),
        ],
    },
    "e-commerce-marketplaces": {
        "category": [
            ("how to start selling on Amazon FBA", 0.9),
            ("best multi-channel ecommerce platform", 0.65),
            ("inventory management for Etsy and Shopify", 0.7),
        ],
        "comparison": [
            ("Amazon FBA vs FBM cost breakdown", 0.78),
            ("Etsy vs Amazon Handmade", 0.6),
            ("Walmart Marketplace vs Amazon", 0.55),
        ],
        "problem": [
            ("Amazon listing suppressed for variation issue", 0.55),
            ("how to win the Buy Box on Amazon", 0.7),
            ("Etsy shop traffic dropped after algorithm change", 0.5),
        ],
        "local": [
            ("Amazon FBA prep center near me", 0.45),
            ("3PL warehouse Atlanta", 0.32),
        ],
    },
    "education-edtech": {
        "category": [
            ("best learning management systems for K-12", 0.7),
            ("AI tutoring tools for math", 0.85),
            ("free coding platforms for kids", 0.78),
            ("online language learning apps for adults", 0.82),
        ],
        "comparison": [
            ("Duolingo vs Babbel vs Pimsleur", 0.88),
            ("Khan Academy vs IXL", 0.65),
            ("Canvas vs Schoology vs Google Classroom", 0.6),
        ],
        "problem": [
            ("how to keep middle schoolers engaged in remote learning", 0.55),
            ("LMS integration with Google Workspace", 0.5),
            ("how to detect AI-written essays", 0.85),
        ],
        "local": [
            ("ACT prep tutors near me", 0.6),
            ("private math tutor Brooklyn", 0.45),
        ],
    },
    "financial-services": {
        "category": [
            ("best high yield savings accounts 2025", 0.95),
            ("robo-advisors with low fees", 0.78),
            ("best business bank account for LLC", 0.85),
            ("treasury management for startups", 0.6),
        ],
        "comparison": [
            ("Mercury vs Brex vs Ramp", 0.88),
            ("Wealthfront vs Betterment 2025", 0.8),
            ("Chase Sapphire vs Amex Gold", 0.92),
        ],
        "problem": [
            ("how to file 1099 for contractors", 0.65),
            ("ACH transfer stuck pending for 5 days", 0.45),
            ("how to set up automated investing", 0.6),
        ],
        "local": [
            ("financial advisor near me fee only", 0.7),
            ("CPA for small business Brooklyn", 0.5),
        ],
    },
    "food-beverage": {
        "category": [
            ("best meal kit delivery service 2025", 0.92),
            ("non-alcoholic craft beer brands", 0.78),
            ("organic baby food delivery", 0.6),
            ("best espresso machine under 500", 0.88),
        ],
        "comparison": [
            ("HelloFresh vs Blue Apron vs Home Chef", 0.85),
            ("Athletic Brewing vs Heineken 0.0", 0.55),
            ("Breville Barista Express vs Pro", 0.7),
        ],
        "problem": [
            ("how to make sourdough starter from scratch", 0.88),
            ("cooking bread pudding without raisins", 0.5),
            ("how to store fresh herbs longer", 0.78),
            ("why is my pizza dough not rising", 0.6),
        ],
        "local": [
            ("best ramen near me open late", 0.85),
            ("vegan bakery Brooklyn", 0.6),
            ("farm to table restaurant Austin", 0.55),
        ],
    },
    "healthcare-telemedicine": {
        "category": [
            ("best telehealth services for therapy", 0.88),
            ("online doctor for prescription refills", 0.82),
            ("at-home blood test kits", 0.7),
            ("hims alternatives for hair loss treatment", 0.6),
        ],
        "comparison": [
            ("Teladoc vs Amwell vs MDLIVE", 0.65),
            ("BetterHelp vs Talkspace 2025", 0.8),
            ("Ro vs Hims for ED treatment", 0.55),
        ],
        "problem": [
            ("how to get a prescription online same day", 0.7),
            ("does insurance cover telehealth therapy", 0.78),
            ("can a doctor diagnose UTI online", 0.55),
        ],
        "local": [
            ("urgent care near me open now", 0.95),
            ("primary care doctor accepting new patients", 0.8),
            ("dermatologist near me with weekend hours", 0.6),
        ],
    },
    "hospitality-travel": {
        "category": [
            ("best travel credit cards 2025", 0.92),
            ("affordable beach resorts in Mexico", 0.85),
            ("digital nomad friendly cities Europe", 0.78),
            ("luxury safari Tanzania vs Kenya", 0.55),
        ],
        "comparison": [
            ("Airbnb vs Vrbo vs hotel for families", 0.7),
            ("Marriott Bonvoy vs Hilton Honors", 0.78),
            ("Expedia vs Booking.com vs Hotels.com", 0.62),
        ],
        "problem": [
            ("how to use credit card points for international flights", 0.7),
            ("Airbnb host cancelled day before check-in", 0.5),
            ("best time to book domestic flights for cheap", 0.85),
        ],
        "local": [
            ("pet friendly hotels near me", 0.78),
            ("boutique hotels Lisbon old town", 0.55),
            ("late check out hotels Las Vegas strip", 0.45),
        ],
    },
    "insurance": {
        "category": [
            ("cheapest car insurance for young drivers", 0.92),
            ("best term life insurance no medical exam", 0.78),
            ("renters insurance for college students", 0.7),
            ("pet insurance with no waiting period", 0.65),
        ],
        "comparison": [
            ("Geico vs Progressive vs State Farm", 0.88),
            ("Lemonade vs Hippo for homeowners", 0.55),
            ("Trupanion vs Healthy Paws pet insurance", 0.5),
        ],
        "problem": [
            ("how to lower car insurance after accident", 0.7),
            ("home insurance won't cover roof damage", 0.55),
            ("can I cancel insurance after one month", 0.6),
        ],
        "local": [
            ("independent insurance agent near me", 0.6),
            ("auto insurance Florida cheapest", 0.7),
        ],
    },
    "legal-services": {
        "category": [
            ("how much does a divorce lawyer cost", 0.85),
            ("trademark registration online services", 0.6),
            ("estate planning checklist 2025", 0.7),
            ("small claims court process", 0.62),
        ],
        "comparison": [
            ("LegalZoom vs Rocket Lawyer", 0.7),
            ("Atticus vs LegalZoom for wills", 0.4),
            ("Stripe Atlas vs Clerky for incorporation", 0.55),
        ],
        "problem": [
            ("how to respond to a cease and desist", 0.55),
            ("landlord won't return security deposit", 0.78),
            ("how to register an LLC in Delaware as non-resident", 0.6),
        ],
        "local": [
            ("immigration lawyer near me free consultation", 0.78),
            ("personal injury attorney Houston", 0.7),
            ("divorce mediator Seattle", 0.5),
        ],
    },
    "local-services-hvac": {
        "category": [
            ("how often to service HVAC system", 0.7),
            ("best heat pump brands 2025", 0.78),
            ("HVAC maintenance plans worth it", 0.55),
        ],
        "comparison": [
            ("Carrier vs Trane vs Lennox heat pumps", 0.7),
            ("Mini split vs central AC cost", 0.85),
            ("Goodman vs Rheem furnace", 0.5),
        ],
        "problem": [
            ("AC blowing warm air after recharge", 0.6),
            ("furnace short cycling causes", 0.55),
            ("how much does HVAC replacement cost 2025", 0.8),
        ],
        "local": [
            ("HVAC repair near me 24 hour", 0.92),
            ("heat pump installer Phoenix", 0.55),
            ("emergency furnace repair Boston", 0.65),
        ],
    },
    "local-services-health-wellness": {
        "category": [
            ("massage therapy types compared", 0.55),
            ("benefits of cold plunge therapy", 0.85),
            ("strength training for over 50", 0.78),
        ],
        "comparison": [
            ("CrossFit vs F45 vs Orangetheory", 0.7),
            ("Pilates vs yoga for back pain", 0.62),
        ],
        "problem": [
            ("how to recover faster from leg day", 0.6),
            ("best stretches for tight hips desk worker", 0.7),
            ("can chiropractor help with herniated disc", 0.5),
        ],
        "local": [
            ("personal trainer near me women only", 0.7),
            ("yoga studio with sauna Austin", 0.5),
            ("acupuncturist near me", 0.55),
            ("chiropractor open Saturday", 0.65),
        ],
    },
    "local-services-home-services": {
        "category": [
            ("how often to clean dryer vent", 0.55),
            ("when to call a plumber vs DIY", 0.6),
            ("best home security systems no contract", 0.78),
        ],
        "comparison": [
            ("ADT vs SimpliSafe vs Ring Alarm", 0.7),
            ("Angi vs Thumbtack for finding handyman", 0.55),
        ],
        "problem": [
            ("toilet keeps running after flush", 0.78),
            ("garage door opener clicks but doesn't open", 0.5),
            ("how to fix slow drain bathroom sink", 0.7),
        ],
        "local": [
            ("plumber near me 24 hour emergency", 0.95),
            ("electrician open Sunday", 0.7),
            ("handyman Brooklyn brownstone", 0.5),
            ("pest control near me termites", 0.65),
        ],
    },
    "manufacturing-industrial": {
        "category": [
            ("best ERP for small manufacturers", 0.7),
            ("MES software for discrete manufacturing", 0.55),
            ("predictive maintenance platforms", 0.6),
        ],
        "comparison": [
            ("NetSuite vs Sage X3 vs Acumatica", 0.55),
            ("Fishbowl vs Katana vs Cin7", 0.5),
        ],
        "problem": [
            ("how to reduce machine downtime in CNC shop", 0.55),
            ("ISO 9001 audit checklist", 0.6),
            ("how to integrate ERP with shopfloor IoT", 0.45),
        ],
        "local": [
            ("contract manufacturer Detroit", 0.4),
            ("CNC machine shop Los Angeles small batch", 0.35),
        ],
    },
    "media-publishing": {
        "category": [
            ("best newsletter platforms for monetization", 0.85),
            ("podcast hosting platforms 2025", 0.78),
            ("paid newsletter platforms with referrals", 0.65),
        ],
        "comparison": [
            ("Substack vs Beehiiv vs Ghost", 0.9),
            ("Spotify for Podcasters vs Buzzsprout", 0.6),
            ("Medium vs Substack for writers", 0.7),
        ],
        "problem": [
            ("how to grow newsletter past 10000 subscribers", 0.78),
            ("how to repurpose podcast into youtube", 0.7),
            ("Substack RSS feed not working in Apple Podcasts", 0.45),
        ],
        "local": [
            ("podcast studio rental NYC", 0.4),
            ("video editor for creators LA", 0.45),
        ],
    },
    "nonprofit": {
        "category": [
            ("best donor management software for small nonprofits", 0.78),
            ("free fundraising platforms 2025", 0.85),
            ("CRM for nonprofits with grant tracking", 0.65),
            ("how to start a 501c3 in 2025", 0.88),
        ],
        "comparison": [
            ("Bloomerang vs Little Green Light vs DonorPerfect", 0.6),
            ("Givebutter vs Donorbox vs Classy", 0.7),
            ("Salesforce Nonprofit Cloud vs Bloomerang", 0.55),
        ],
        "problem": [
            ("how to write a grant proposal that gets funded", 0.85),
            ("how to recruit volunteers for small nonprofit", 0.7),
            ("nonprofit tax filing 990 deadlines", 0.55),
            ("how to thank donors at scale", 0.5),
        ],
        "local": [
            ("nonprofit attorney near me 501c3 setup", 0.55),
            ("food bank volunteer opportunities Chicago", 0.6),
            ("nonprofit accountant Atlanta", 0.4),
        ],
    },
    "professional-services-consulting": {
        "category": [
            ("best management consulting firms 2025", 0.7),
            ("fractional CFO services for startups", 0.85),
            ("strategy consulting career path MBA", 0.62),
        ],
        "comparison": [
            ("McKinsey vs BCG vs Bain culture", 0.78),
            ("Deloitte vs Accenture for digital transformation", 0.6),
        ],
        "problem": [
            ("how to price consulting services per hour or value", 0.78),
            ("how to find consulting clients without cold outreach", 0.7),
            ("scope creep in client engagements", 0.5),
        ],
        "local": [
            ("management consultant near me small business", 0.55),
            ("HR consultant New York City", 0.5),
        ],
    },
    "real-estate": {
        "category": [
            ("best mortgage rates 2025 first time buyer", 0.95),
            ("how to invest in real estate with little money", 0.92),
            ("FHA vs conventional loan", 0.85),
            ("buying foreclosed homes guide", 0.65),
        ],
        "comparison": [
            ("Zillow vs Redfin for buyers", 0.78),
            ("Compass vs Coldwell Banker", 0.55),
            ("Roofstock vs Fundrise REIT", 0.6),
        ],
        "problem": [
            ("how to buy a house with bad credit", 0.78),
            ("HELOC vs cash out refi 2025", 0.7),
            ("how to challenge a low appraisal", 0.65),
        ],
        "local": [
            ("real estate agent near me first time buyer", 0.85),
            ("homes for sale Austin under 500k", 0.78),
            ("mortgage broker NYC self employed", 0.6),
        ],
    },
}


class Command(BaseCommand):
    help = "Seed the prompt library with curated real-world prompts per industry."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete all source=manual prompts before seeding.",
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        if opts.get("reset"):
            n = Prompt.objects.filter(source=PromptSource.MANUAL).count()
            Prompt.objects.filter(source=PromptSource.MANUAL).delete()
            self.stdout.write(self.style.WARNING(f"Deleted {n} manual prompts."))

        valid_buckets = {b.value for b in IntentBucket}
        created = 0
        updated = 0
        skipped_industries: list[str] = []

        for slug, buckets in SEED.items():
            try:
                industry = Industry.objects.get(slug=slug)
            except Industry.DoesNotExist:
                skipped_industries.append(slug)
                continue
            for bucket, items in buckets.items():
                if bucket not in valid_buckets:
                    raise ValueError(f"Unknown intent bucket: {bucket}")
                for text, demand in items:
                    th = text_hash(text)
                    obj, was_created = Prompt.objects.update_or_create(
                        industry=industry,
                        text_hash=th,
                        defaults={
                            "text": text,
                            "intent_bucket": bucket,
                            "source": PromptSource.MANUAL,
                            "demand_score": float(demand),
                            "is_active": True,
                            "language": "en",
                        },
                    )
                    if was_created:
                        created += 1
                    else:
                        updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed complete: created={created} updated={updated} "
                f"covered_industries={len(SEED) - len(skipped_industries)}/20"
            )
        )
        if skipped_industries:
            self.stdout.write(
                self.style.WARNING(
                    "Skipped (industry not seeded): " + ", ".join(skipped_industries)
                )
            )
