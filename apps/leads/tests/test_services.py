import pytest

from apps.accounts.tests.factories import UserFactory
from apps.leads.models import Lead, LeadNote
from apps.leads.services.lead_service import LeadService
from apps.leads.services.scoring_service import DEFAULT_WEIGHTS, ScoringService
from apps.leads.tests.factories import (
    LeadFactory,
    PageEventFactory,
    ScoringConfigFactory,
    VisitorFactory,
    WebsiteFactory,
)
from core.exceptions import ResourceNotFound
from core.utils.constants import LeadStatus


@pytest.mark.django_db
class TestLeadService:
    def test_get_leads_returns_all_for_website(self):
        website = WebsiteFactory()
        v1 = VisitorFactory(website=website)
        v2 = VisitorFactory(website=website)
        LeadFactory(visitor=v1, website=website, score=80)
        LeadFactory(visitor=v2, website=website, score=50)

        leads = LeadService.get_leads(website_id=str(website.id))
        assert leads.count() == 2

    def test_get_leads_orders_by_score_desc(self):
        website = WebsiteFactory()
        v1 = VisitorFactory(website=website)
        v2 = VisitorFactory(website=website)
        LeadFactory(visitor=v1, website=website, score=30)
        LeadFactory(visitor=v2, website=website, score=90)

        leads = list(LeadService.get_leads(website_id=str(website.id)))
        assert leads[0].score == 90
        assert leads[1].score == 30

    def test_get_leads_filters_by_status(self):
        website = WebsiteFactory()
        v1 = VisitorFactory(website=website)
        v2 = VisitorFactory(website=website)
        LeadFactory(visitor=v1, website=website, status=LeadStatus.NEW)
        LeadFactory(visitor=v2, website=website, status=LeadStatus.QUALIFIED)

        leads = LeadService.get_leads(website_id=str(website.id), status=LeadStatus.NEW)
        assert leads.count() == 1
        assert leads.first().status == LeadStatus.NEW

    def test_get_leads_filters_by_min_score(self):
        website = WebsiteFactory()
        v1 = VisitorFactory(website=website)
        v2 = VisitorFactory(website=website)
        LeadFactory(visitor=v1, website=website, score=30)
        LeadFactory(visitor=v2, website=website, score=80)

        leads = LeadService.get_leads(website_id=str(website.id), min_score=50)
        assert leads.count() == 1
        assert leads.first().score == 80

    def test_get_leads_excludes_other_websites(self):
        w1 = WebsiteFactory()
        w2 = WebsiteFactory(user=w1.user)
        v1 = VisitorFactory(website=w1)
        v2 = VisitorFactory(website=w2)
        LeadFactory(visitor=v1, website=w1)
        LeadFactory(visitor=v2, website=w2)

        leads = LeadService.get_leads(website_id=str(w1.id))
        assert leads.count() == 1

    def test_get_lead_returns_correct_lead(self):
        website = WebsiteFactory()
        visitor = VisitorFactory(website=website)
        lead = LeadFactory(visitor=visitor, website=website)

        result = LeadService.get_lead(website_id=str(website.id), lead_id=str(lead.id))
        assert result.id == lead.id

    def test_get_lead_raises_not_found_for_wrong_website(self):
        w1 = WebsiteFactory()
        w2 = WebsiteFactory(user=w1.user)
        visitor = VisitorFactory(website=w1)
        lead = LeadFactory(visitor=visitor, website=w1)

        with pytest.raises(ResourceNotFound):
            LeadService.get_lead(website_id=str(w2.id), lead_id=str(lead.id))

    def test_get_lead_raises_not_found_for_missing_id(self):
        website = WebsiteFactory()
        import uuid
        with pytest.raises(ResourceNotFound):
            LeadService.get_lead(website_id=str(website.id), lead_id=str(uuid.uuid4()))

    def test_update_status_changes_lead_status(self):
        user = UserFactory()
        website = WebsiteFactory(user=user)
        visitor = VisitorFactory(website=website)
        lead = LeadFactory(visitor=visitor, website=website, status=LeadStatus.NEW)

        updated = LeadService.update_status(lead=lead, status=LeadStatus.CONTACTED, user=user)
        lead.refresh_from_db()
        assert lead.status == LeadStatus.CONTACTED
        assert updated.status == LeadStatus.CONTACTED

    def test_add_note_creates_note(self):
        user = UserFactory()
        website = WebsiteFactory(user=user)
        visitor = VisitorFactory(website=website)
        lead = LeadFactory(visitor=visitor, website=website)

        note = LeadService.add_note(lead=lead, content="Test note content", user=user)
        assert note.content == "Test note content"
        assert note.author == user
        assert note.lead == lead
        assert LeadNote.objects.filter(lead=lead).count() == 1

    def test_export_csv_returns_csv_string(self):
        website = WebsiteFactory()
        visitor = VisitorFactory(website=website)
        LeadFactory(visitor=visitor, website=website, email="test@example.com", company="Acme")

        csv_data = LeadService.export_csv(website_id=str(website.id))
        assert "ID,Score,Status,Email,Company,Source,Created At" in csv_data
        assert "test@example.com" in csv_data
        assert "Acme" in csv_data

    def test_export_csv_empty_website(self):
        website = WebsiteFactory()
        csv_data = LeadService.export_csv(website_id=str(website.id))
        assert "ID,Score,Status,Email,Company,Source,Created At" in csv_data


@pytest.mark.django_db
class TestScoringService:
    def test_compute_score_counts_pageviews(self):
        visitor = VisitorFactory()
        PageEventFactory(visitor=visitor, event_type="pageview", url="https://example.com/about")
        PageEventFactory(visitor=visitor, event_type="pageview", url="https://example.com/blog")

        score = ScoringService.compute_score(visitor=visitor)
        assert score >= 2 * DEFAULT_WEIGHTS["page_views"]

    def test_compute_score_adds_pricing_page_bonus(self):
        visitor = VisitorFactory()
        PageEventFactory(visitor=visitor, event_type="pageview", url="https://example.com/pricing")

        score = ScoringService.compute_score(visitor=visitor)
        expected_min = DEFAULT_WEIGHTS["page_views"] + DEFAULT_WEIGHTS["pricing_page_visit"]
        assert score >= expected_min

    def test_compute_score_adds_contact_page_bonus(self):
        visitor = VisitorFactory()
        PageEventFactory(visitor=visitor, event_type="pageview", url="https://example.com/contact")

        score = ScoringService.compute_score(visitor=visitor)
        expected_min = DEFAULT_WEIGHTS["page_views"] + DEFAULT_WEIGHTS["contact_page_visit"]
        assert score >= expected_min

    def test_compute_score_adds_form_submit_bonus(self):
        visitor = VisitorFactory()
        PageEventFactory(visitor=visitor, event_type="form_submit", url="https://example.com/contact")

        score = ScoringService.compute_score(visitor=visitor)
        assert score >= DEFAULT_WEIGHTS["form_submit"]

    def test_compute_score_adds_return_visit_bonus(self):
        visitor = VisitorFactory(visit_count=3)
        score = ScoringService.compute_score(visitor=visitor)
        assert score >= DEFAULT_WEIGHTS["return_visit"]

    def test_compute_score_no_return_visit_bonus_for_first_visit(self):
        visitor = VisitorFactory(visit_count=1)
        score = ScoringService.compute_score(visitor=visitor)
        # No events, no return visit bonus
        assert score == 0

    def test_compute_score_adds_time_on_site_bonus(self):
        visitor = VisitorFactory()
        # 2 minutes = 120000ms
        PageEventFactory(visitor=visitor, event_type="pageview", url="https://example.com/", time_on_page_ms=120000)

        score = ScoringService.compute_score(visitor=visitor)
        # Should include 2 minutes * 1 point/minute = 2 extra points
        assert score >= DEFAULT_WEIGHTS["page_views"] + 2 * DEFAULT_WEIGHTS["time_on_site_min"]

    def test_compute_score_adds_high_scroll_depth_bonus(self):
        visitor = VisitorFactory()
        PageEventFactory(visitor=visitor, event_type="scroll", url="https://example.com/", scroll_depth=80)

        score = ScoringService.compute_score(visitor=visitor)
        assert score >= DEFAULT_WEIGHTS["high_scroll_depth"]

    def test_compute_score_no_high_scroll_bonus_below_threshold(self):
        visitor = VisitorFactory()
        PageEventFactory(visitor=visitor, event_type="scroll", url="https://example.com/", scroll_depth=50)

        score = ScoringService.compute_score(visitor=visitor)
        assert score < DEFAULT_WEIGHTS["high_scroll_depth"]

    def test_compute_score_capped_at_100(self):
        visitor = VisitorFactory(visit_count=5)
        # Add many high-value events
        for _ in range(10):
            PageEventFactory(visitor=visitor, event_type="form_submit", url="https://example.com/contact")
            PageEventFactory(visitor=visitor, event_type="pageview", url="https://example.com/pricing")

        score = ScoringService.compute_score(visitor=visitor)
        assert score == 100

    def test_compute_score_uses_scoring_config_weights(self):
        website = WebsiteFactory()
        visitor = VisitorFactory(website=website)
        # Override form_submit weight to 0
        ScoringConfigFactory(website=website, weights={"form_submit": 0})
        PageEventFactory(visitor=visitor, event_type="form_submit", url="https://example.com/")

        score = ScoringService.compute_score(visitor=visitor)
        # form_submit weight is 0, so score should be 0
        assert score == 0

    def test_rescore_website_updates_visitor_lead_scores(self):
        website = WebsiteFactory()
        visitor = VisitorFactory(website=website)
        PageEventFactory(visitor=visitor, event_type="pageview", url="https://example.com/pricing")

        count = ScoringService.rescore_website(website_id=str(website.id))
        assert count == 1
        visitor.refresh_from_db()
        assert visitor.lead_score > 0

    def test_rescore_website_creates_lead_for_significant_score(self):
        website = WebsiteFactory()
        visitor = VisitorFactory(website=website)
        # Add events that will produce a score >= 10
        for _ in range(5):
            PageEventFactory(visitor=visitor, event_type="pageview", url="https://example.com/pricing")

        ScoringService.rescore_website(website_id=str(website.id))
        assert Lead.objects.filter(visitor=visitor).exists()

    def test_rescore_website_updates_existing_lead(self):
        website = WebsiteFactory()
        visitor = VisitorFactory(website=website)
        existing_lead = LeadFactory(visitor=visitor, website=website, score=20)
        for _ in range(5):
            PageEventFactory(visitor=visitor, event_type="pageview", url="https://example.com/pricing")

        ScoringService.rescore_website(website_id=str(website.id))
        existing_lead.refresh_from_db()
        assert existing_lead.score > 20
