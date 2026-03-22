import factory
from django.utils import timezone
from factory.django import DjangoModelFactory

from apps.accounts.tests.factories import UserFactory
from apps.analytics.models import PageEvent, Visitor
from apps.leads.models import (
    CampaignRecipient,
    EmailCampaign,
    Lead,
    LeadNote,
    LeadSegment,
    ScoringConfig,
)
from apps.websites.models import Website, WebsiteSettings
from core.utils.constants import LeadStatus


class WebsiteFactory(DjangoModelFactory):
    class Meta:
        model = Website

    user = factory.SubFactory(UserFactory)
    url = factory.Sequence(lambda n: f"https://site{n}.example.com")
    name = factory.Sequence(lambda n: f"Site {n}")
    is_active = True

    @factory.post_generation
    def settings(obj, create, extracted, **kwargs):
        if create:
            WebsiteSettings.objects.create(website=obj)


class VisitorFactory(DjangoModelFactory):
    class Meta:
        model = Visitor

    website = factory.SubFactory(WebsiteFactory)
    fingerprint_hash = factory.Sequence(lambda n: f"fp{n:064d}")
    geo_country = "US"
    device_type = "desktop"
    visit_count = 1
    lead_score = 0


class PageEventFactory(DjangoModelFactory):
    class Meta:
        model = PageEvent

    visitor = factory.SubFactory(VisitorFactory)
    website = factory.LazyAttribute(lambda o: o.visitor.website)
    url = "https://example.com/page"
    event_type = "pageview"
    timestamp = factory.LazyFunction(timezone.now)


class LeadFactory(DjangoModelFactory):
    class Meta:
        model = Lead

    visitor = factory.SubFactory(VisitorFactory)
    website = factory.LazyAttribute(lambda o: o.visitor.website)
    score = 50
    status = LeadStatus.NEW
    email = factory.Sequence(lambda n: f"lead{n}@example.com")
    name = factory.Faker("name")
    company = factory.Faker("company")


class LeadNoteFactory(DjangoModelFactory):
    class Meta:
        model = LeadNote

    lead = factory.SubFactory(LeadFactory)
    author = factory.SubFactory(UserFactory)
    content = factory.Faker("sentence")


class LeadSegmentFactory(DjangoModelFactory):
    class Meta:
        model = LeadSegment

    website = factory.SubFactory(WebsiteFactory)
    name = factory.Sequence(lambda n: f"Segment {n}")
    rules = factory.LazyFunction(dict)
    created_by = factory.SubFactory(UserFactory)


class ScoringConfigFactory(DjangoModelFactory):
    class Meta:
        model = ScoringConfig

    website = factory.SubFactory(WebsiteFactory)
    weights = factory.LazyFunction(dict)
    threshold = 70


class EmailCampaignFactory(DjangoModelFactory):
    class Meta:
        model = EmailCampaign

    website = factory.SubFactory(WebsiteFactory)
    created_by = factory.SubFactory(UserFactory)
    subject = factory.Sequence(lambda n: f"Campaign {n}")
    body = "<p>Hello!</p>"
    status = EmailCampaign.STATUS_DRAFT


class CampaignRecipientFactory(DjangoModelFactory):
    class Meta:
        model = CampaignRecipient

    campaign = factory.SubFactory(EmailCampaignFactory)
    lead = factory.SubFactory(LeadFactory)
    status = CampaignRecipient.STATUS_QUEUED
