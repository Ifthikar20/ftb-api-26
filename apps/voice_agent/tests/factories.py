"""Factory-boy factories for voice agent models.

These factories follow the same conventions as ``apps.accounts.tests.factories``
and ``apps.leads.tests.factories``. Use them to create realistic test data
without manual boilerplate.
"""

from datetime import timedelta

import factory
from django.utils import timezone
from factory.django import DjangoModelFactory

from apps.voice_agent.models import (
    AgentConfig,
    AgentContextDocument,
    CalendarEvent,
    CallbackReminder,
    CallCampaign,
    CallExtraction,
    CallLog,
    CallTarget,
    CallTodo,
    DoNotCallEntry,
    PhoneNumber,
    VoiceUsageMonthly,
)


# ── Dependent factories (imported, not redefined) ────────────────────────────

class _UserFactory(DjangoModelFactory):
    """Minimal inline user factory so this module is self-contained.

    Prefer ``apps.accounts.tests.factories.UserFactory`` in tests that need
    full user features. This one exists only to satisfy ForeignKey defaults.
    """

    class Meta:
        model = "accounts.User"

    email = factory.Sequence(lambda n: f"voice-user-{n}@example.com")
    full_name = factory.Faker("name")
    is_active = True

    @factory.post_generation
    def password(obj, create, extracted, **kwargs):
        obj.set_password(extracted or "TestPass123!")
        if create:
            obj.save(update_fields=["password"])


class _WebsiteFactory(DjangoModelFactory):
    class Meta:
        model = "websites.Website"

    name = factory.Sequence(lambda n: f"Voice Site {n}")
    url = factory.Sequence(lambda n: f"https://voice-site-{n}.test")
    user = factory.SubFactory(_UserFactory)


# ── Voice agent factories ────────────────────────────────────────────────────


class PhoneNumberFactory(DjangoModelFactory):
    class Meta:
        model = PhoneNumber

    website = factory.SubFactory(_WebsiteFactory)
    number = factory.Sequence(lambda n: f"+1555000{n:04d}")
    label = factory.Faker("bs")
    provider = PhoneNumber.PROVIDER_TELNYX
    is_active = True
    forwarded_to_agent = True
    is_verified = True
    verified_at = factory.LazyFunction(timezone.now)


class AgentConfigFactory(DjangoModelFactory):
    class Meta:
        model = AgentConfig

    website = factory.SubFactory(_WebsiteFactory)
    is_active = True
    greeting_message = "Hello! How can I help you today?"
    business_name = factory.Faker("company")
    timezone = "America/Chicago"
    appointment_duration_minutes = 30
    business_hours = factory.LazyFunction(lambda: {
        "monday": {"start": "09:00", "end": "17:00"},
        "tuesday": {"start": "09:00", "end": "17:00"},
        "wednesday": {"start": "09:00", "end": "17:00"},
        "thursday": {"start": "09:00", "end": "17:00"},
        "friday": {"start": "09:00", "end": "17:00"},
    })


class AgentContextDocumentFactory(DjangoModelFactory):
    class Meta:
        model = AgentContextDocument

    website = factory.SubFactory(_WebsiteFactory)
    title = factory.Sequence(lambda n: f"KB Document {n}")
    content = factory.Faker("paragraph")
    is_active = True
    sort_order = factory.Sequence(lambda n: n)


class CallLogFactory(DjangoModelFactory):
    class Meta:
        model = CallLog

    website = factory.SubFactory(_WebsiteFactory)
    caller_phone = factory.Sequence(lambda n: f"+1202555{n:04d}")
    direction = CallLog.DIRECTION_INBOUND
    status = CallLog.STATUS_COMPLETED
    duration_seconds = 120
    started_at = factory.LazyFunction(lambda: timezone.now() - timedelta(minutes=2))
    ended_at = factory.LazyFunction(timezone.now)

    class Params:
        outbound = factory.Trait(direction=CallLog.DIRECTION_OUTBOUND)
        missed = factory.Trait(
            status=CallLog.STATUS_MISSED,
            duration_seconds=0,
        )
        with_transcript = factory.Trait(
            transcript="Agent: Hello! How can I help you today?\n"
                       "Caller: I'd like to schedule an appointment please.\n"
                       "Agent: Of course! What date works best for you?",
            summary="Caller requested an appointment.",
            sentiment="positive",
            call_intent="appointment",
        )
        with_lead_signals = factory.Trait(
            caller_name="Jane Smith",
            caller_email="jane@example.com",
            caller_company="Acme Corp",
            call_intent="sales",
            sentiment="positive",
            is_possible_lead=True,
            lead_score=75,
        )


class CalendarEventFactory(DjangoModelFactory):
    class Meta:
        model = CalendarEvent

    website = factory.SubFactory(_WebsiteFactory)
    title = factory.Sequence(lambda n: f"Appointment {n}")
    attendee_name = factory.Faker("name")
    attendee_phone = factory.Sequence(lambda n: f"+1202555{n:04d}")
    attendee_email = factory.Faker("email")
    status = CalendarEvent.STATUS_SCHEDULED
    start_time = factory.LazyFunction(lambda: timezone.now() + timedelta(days=1))
    end_time = factory.LazyFunction(lambda: timezone.now() + timedelta(days=1, minutes=30))
    timezone = "UTC"


class CallbackReminderFactory(DjangoModelFactory):
    class Meta:
        model = CallbackReminder

    website = factory.SubFactory(_WebsiteFactory)
    contact_name = factory.Faker("name")
    contact_phone = factory.Sequence(lambda n: f"+1202555{n:04d}")
    reason = factory.Faker("sentence")
    remind_at = factory.LazyFunction(lambda: timezone.now() + timedelta(hours=1))
    status = CallbackReminder.STATUS_PENDING


class CallExtractionFactory(DjangoModelFactory):
    class Meta:
        model = CallExtraction

    call_log = factory.SubFactory(CallLogFactory)
    caller_info = factory.LazyFunction(lambda: {
        "name": "Jane Smith",
        "phone": "+12025551234",
        "email": "jane@example.com",
        "company": "Acme Corp",
    })
    call_summary = "Caller inquired about services and requested an appointment."
    call_category = "appointment"
    sentiment = "positive"
    follow_ups = factory.LazyFunction(lambda: [
        {"description": "Send pricing sheet", "urgency": "within_24h"},
    ])
    appointments_detected = factory.LazyFunction(lambda: [])
    model_used = "gpt-4o-mini (test)"
    processing_time_ms = 450


class CallTodoFactory(DjangoModelFactory):
    class Meta:
        model = CallTodo

    website = factory.SubFactory(_WebsiteFactory)
    call_log = factory.SubFactory(CallLogFactory)
    description = factory.Faker("sentence")
    priority = CallTodo.PRIORITY_MEDIUM
    status = CallTodo.STATUS_OPEN


class CallCampaignFactory(DjangoModelFactory):
    class Meta:
        model = CallCampaign

    website = factory.SubFactory(_WebsiteFactory)
    name = factory.Sequence(lambda n: f"Campaign {n}")
    welcome_message = "Hi! This is a quick call about our services."
    from_number = factory.SubFactory(
        PhoneNumberFactory,
        website=factory.SelfAttribute("..website"),
        livekit_outbound_trunk_id="trunk_test_123",
    )
    status = CallCampaign.STATUS_DRAFT
    max_concurrent_calls = 3
    calls_per_minute = 10
    respect_business_hours = False


class CallTargetFactory(DjangoModelFactory):
    class Meta:
        model = CallTarget

    campaign = factory.SubFactory(CallCampaignFactory)
    phone = factory.Sequence(lambda n: f"+1555123{n:04d}")
    name = factory.Faker("name")
    status = CallTarget.STATUS_PENDING
    max_attempts = 2


class DoNotCallEntryFactory(DjangoModelFactory):
    class Meta:
        model = DoNotCallEntry

    phone = factory.Sequence(lambda n: f"+1555999{n:04d}")
    reason = "Customer requested removal from call list"


class VoiceUsageMonthlyFactory(DjangoModelFactory):
    class Meta:
        model = VoiceUsageMonthly

    website = factory.SubFactory(_WebsiteFactory)
    year_month = factory.LazyFunction(lambda: timezone.now().strftime("%Y-%m"))
    total_calls = 10
    inbound_calls = 7
    outbound_calls = 3
    total_seconds = 3600
    billable_minutes = 60
