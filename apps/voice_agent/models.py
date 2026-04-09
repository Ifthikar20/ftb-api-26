import uuid

from django.conf import settings
from django.db import models

from core.mixins.timestamp_mixin import TimestampMixin


class PhoneNumber(TimestampMixin):
    """Work phone numbers added by the user. Calls from these can be forwarded to the AI agent."""

    PROVIDER_TELNYX = "telnyx"
    PROVIDER_TWILIO = "twilio"
    PROVIDER_RETELL = "retell"
    PROVIDER_OTHER = "other"
    PROVIDER_CHOICES = [
        (PROVIDER_TELNYX, "Telnyx"),
        (PROVIDER_TWILIO, "Twilio"),
        (PROVIDER_RETELL, "Retell AI"),
        (PROVIDER_OTHER, "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    website = models.ForeignKey(
        "websites.Website", on_delete=models.CASCADE, related_name="phone_numbers"
    )
    number = models.CharField(
        max_length=30,
        help_text="E.164 format, e.g. +12025551234",
    )
    label = models.CharField(
        max_length=100, blank=True,
        help_text="Human-readable label, e.g. 'Main Line', 'Sales Line'",
    )
    provider = models.CharField(
        max_length=20, choices=PROVIDER_CHOICES, default=PROVIDER_TELNYX
    )
    is_active = models.BooleanField(default=True)
    forwarded_to_agent = models.BooleanField(
        default=True,
        help_text="Route inbound calls from this number to the AI voice agent.",
    )
    telnyx_trunk_id = models.CharField(
        max_length=200, blank=True,
        help_text="Telnyx SIP connection / trunk ID this caller-ID dials out from.",
    )
    livekit_outbound_trunk_id = models.CharField(
        max_length=200, blank=True,
        help_text="LiveKit-side outbound SIP trunk ID returned from CreateSIPOutboundTrunk.",
    )
    is_verified = models.BooleanField(
        default=False,
        help_text="True once the user has completed SMS/call MFA proving ownership of this number.",
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "voice_agent_phonenumber"
        ordering = ["created_at"]
        unique_together = [("website", "number")]

    def __str__(self):
        label = f" ({self.label})" if self.label else ""
        return f"{self.number}{label}"


class AgentContextDocument(TimestampMixin):
    """Markdown knowledge-base documents injected into the agent system prompt at call time."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    website = models.ForeignKey(
        "websites.Website", on_delete=models.CASCADE, related_name="agent_context_docs"
    )
    title = models.CharField(max_length=200, help_text="e.g. 'Services & Pricing', 'FAQs'")
    content = models.TextField(help_text="Markdown content injected into the AI system prompt.")
    is_active = models.BooleanField(
        default=True, help_text="Only active documents are included in calls."
    )
    sort_order = models.IntegerField(
        default=0, help_text="Lower values appear first in the prompt."
    )

    class Meta:
        db_table = "voice_agent_contextdocument"
        ordering = ["sort_order", "created_at"]

    def __str__(self):
        return f"{self.title} ({'active' if self.is_active else 'inactive'})"


class AgentConfig(TimestampMixin):
    """Per-website voice agent configuration. Supports Retell AI, LiveKit, or fully self-hosted."""

    website = models.OneToOneField(
        "websites.Website", on_delete=models.CASCADE, related_name="voice_agent_config"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Always-on. Retained for backward compatibility; agent is enabled by default.",
    )
    retell_agent_id = models.CharField(max_length=200, blank=True)
    phone_number = models.CharField(max_length=30, blank=True)
    greeting_message = models.TextField(
        default="Hello! Thank you for calling. How can I help you today?"
    )
    system_prompt = models.TextField(
        default=(
            "You are a friendly and professional voice assistant. "
            "Help callers schedule appointments, answer questions about the business, "
            "and capture their contact information. Always confirm details before booking."
        )
    )
    business_context = models.TextField(
        blank=True,
        default="",
        help_text="Markdown knowledge base about the business — services, pricing, FAQs, policies, etc.",
    )
    business_name = models.CharField(max_length=200, blank=True)
    forwarding_number = models.CharField(
        max_length=30,
        blank=True,
        help_text="The SIP/Telnyx number that the business forwards their calls to.",
    )
    business_hours = models.JSONField(
        default=dict,
        help_text="Business hours per day, e.g. {'monday': {'start': '09:00', 'end': '17:00'}}",
    )
    appointment_duration_minutes = models.IntegerField(default=30)
    timezone = models.CharField(max_length=50, default="UTC")

    class Meta:
        db_table = "voice_agent_config"

    def __str__(self):
        return f"VoiceAgent({self.website.name}, active={self.is_active})"


class PhoneVerification(TimestampMixin):
    """Short-lived MFA challenge issued when a user adds a phone number.

    The user enters a number, we send a 6-digit code via SMS or place an
    automated call (through our telephony vendor) that reads the code aloud.
    The user posts the code back; on success the number is marked verified
    and may be saved as a PhoneNumber.
    """

    CHANNEL_SMS = "sms"
    CHANNEL_CALL = "call"
    CHANNEL_CHOICES = [(CHANNEL_SMS, "SMS"), (CHANNEL_CALL, "Voice call")]

    STATUS_PENDING = "pending"
    STATUS_VERIFIED = "verified"
    STATUS_EXPIRED = "expired"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_VERIFIED, "Verified"),
        (STATUS_EXPIRED, "Expired"),
        (STATUS_FAILED, "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    website = models.ForeignKey(
        "websites.Website", on_delete=models.CASCADE, related_name="phone_verifications"
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    number = models.CharField(max_length=30, help_text="E.164 number being verified")
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES, default=CHANNEL_SMS)
    code_hash = models.CharField(max_length=128, help_text="HMAC-SHA256 of the OTP")
    expires_at = models.DateTimeField()
    attempts = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=5)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_PENDING)
    vendor_request_id = models.CharField(
        max_length=200, blank=True,
        help_text="Vendor (Telnyx/Twilio) message or call SID for tracing.",
    )

    class Meta:
        db_table = "voice_agent_phoneverification"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["website", "number", "status"])]

    def __str__(self):
        return f"PhoneVerification({self.number}, {self.status})"


class CallLog(TimestampMixin):
    """Log of every inbound/outbound voice call."""

    DIRECTION_INBOUND = "inbound"
    DIRECTION_OUTBOUND = "outbound"
    DIRECTION_CHOICES = [
        (DIRECTION_INBOUND, "Inbound"),
        (DIRECTION_OUTBOUND, "Outbound"),
    ]

    STATUS_RINGING = "ringing"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_COMPLETED = "completed"
    STATUS_MISSED = "missed"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_RINGING, "Ringing"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_MISSED, "Missed"),
        (STATUS_FAILED, "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    website = models.ForeignKey(
        "websites.Website", on_delete=models.CASCADE, related_name="call_logs"
    )
    external_call_id = models.CharField(
        max_length=200, blank=True, db_index=True,
        help_text="External call identifier (Retell call_id, LiveKit room name, etc.)",
    )
    direction = models.CharField(
        max_length=10, choices=DIRECTION_CHOICES, default=DIRECTION_INBOUND
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_RINGING, db_index=True
    )
    caller_phone = models.CharField(max_length=30, db_index=True)
    caller_name = models.CharField(max_length=200, blank=True)
    caller_email = models.EmailField(blank=True)
    caller_company = models.CharField(max_length=200, blank=True)

    # Call metadata
    duration_seconds = models.IntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    # AI-extracted data
    transcript = models.TextField(blank=True)
    summary = models.TextField(blank=True)
    sentiment = models.CharField(max_length=20, blank=True)
    extracted_data = models.JSONField(
        default=dict,
        help_text="Structured data extracted by AI (name, email, intent, etc.)",
    )
    call_intent = models.CharField(max_length=100, blank=True)

    # Link to lead if identified
    lead = models.ForeignKey(
        "leads.Lead", null=True, blank=True, on_delete=models.SET_NULL, related_name="calls"
    )

    # Transcript-based lead detection (populated by lead_scoring_service after
    # post-call extraction). ``is_possible_lead`` flips True when ``lead_score``
    # crosses the configured threshold; rows then surface in the Lead Detection
    # tab for the user to manually promote into the Lead table.
    # Usage / billing meters. Populated from the LiveKit worker payload at
    # call-finish time and rolled into VoiceUsageMonthly by UsageService.
    billable_seconds = models.PositiveIntegerField(default=0)
    stt_seconds = models.PositiveIntegerField(default=0)
    tts_characters = models.PositiveIntegerField(default=0)
    llm_input_tokens = models.PositiveIntegerField(default=0)
    llm_output_tokens = models.PositiveIntegerField(default=0)
    estimated_cost_usd = models.DecimalField(
        max_digits=8, decimal_places=4, default=0,
        help_text="Per-call cost estimate computed from per-meter unit prices.",
    )

    is_possible_lead = models.BooleanField(default=False, db_index=True)
    lead_score = models.PositiveSmallIntegerField(default=0)
    lead_signals = models.JSONField(
        default=dict,
        blank=True,
        help_text="Per-signal contributions used to compute lead_score (for explainability).",
    )
    lead_promoted_at = models.DateTimeField(null=True, blank=True)
    lead_dismissed_at = models.DateTimeField(null=True, blank=True)

    # Outbound campaign linkage
    campaign = models.ForeignKey(
        "voice_agent.CallCampaign",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="call_logs",
    )
    target = models.ForeignKey(
        "voice_agent.CallTarget",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="call_logs",
    )

    class Meta:
        db_table = "voice_agent_calllog"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["website", "status"]),
            models.Index(fields=["website", "caller_phone"]),
            models.Index(fields=["website", "-created_at"]),
        ]

    def __str__(self):
        return f"Call({self.caller_phone}, {self.status}, {self.duration_seconds}s)"

    @property
    def duration_display(self):
        mins, secs = divmod(self.duration_seconds, 60)
        return f"{mins}m {secs}s"


class VoiceUsageMonthly(TimestampMixin):
    """Pre-aggregated voice agent usage per (website, calendar month).

    Updated incrementally by ``UsageService.record_call`` whenever a call
    finishes. The UI reads from this table directly so the dashboard never
    has to scan ``CallLog``. A nightly reconciler can rebuild rows from
    ``CallLog`` to recover from any worker that crashed mid-update.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    website = models.ForeignKey(
        "websites.Website", on_delete=models.CASCADE, related_name="voice_usage_months"
    )
    year_month = models.CharField(
        max_length=7, help_text="ISO month, e.g. '2026-04'."
    )

    total_calls = models.PositiveIntegerField(default=0)
    inbound_calls = models.PositiveIntegerField(default=0)
    outbound_calls = models.PositiveIntegerField(default=0)

    total_seconds = models.PositiveIntegerField(default=0)
    billable_minutes = models.PositiveIntegerField(default=0)

    llm_input_tokens = models.PositiveBigIntegerField(default=0)
    llm_output_tokens = models.PositiveBigIntegerField(default=0)
    tts_characters = models.PositiveBigIntegerField(default=0)

    estimated_cost_usd = models.DecimalField(
        max_digits=10, decimal_places=4, default=0
    )

    class Meta:
        db_table = "voice_agent_usage_monthly"
        unique_together = [("website", "year_month")]
        ordering = ["-year_month"]
        indexes = [models.Index(fields=["website", "year_month"])]

    def __str__(self):
        return f"VoiceUsage({self.website_id}, {self.year_month}, {self.billable_minutes}m)"


class CalendarEvent(TimestampMixin):
    """Appointments booked via the voice agent."""

    STATUS_SCHEDULED = "scheduled"
    STATUS_CONFIRMED = "confirmed"
    STATUS_CANCELLED = "cancelled"
    STATUS_COMPLETED = "completed"
    STATUS_NO_SHOW = "no_show"
    STATUS_CHOICES = [
        (STATUS_SCHEDULED, "Scheduled"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_NO_SHOW, "No Show"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    website = models.ForeignKey(
        "websites.Website", on_delete=models.CASCADE, related_name="calendar_events"
    )
    call_log = models.ForeignKey(
        CallLog, null=True, blank=True, on_delete=models.SET_NULL, related_name="appointments"
    )
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_SCHEDULED, db_index=True
    )

    # Scheduling
    start_time = models.DateTimeField(db_index=True)
    end_time = models.DateTimeField()
    timezone = models.CharField(max_length=50, default="UTC")

    # Contact
    attendee_name = models.CharField(max_length=200)
    attendee_phone = models.CharField(max_length=30)
    attendee_email = models.EmailField(blank=True)

    # External calendar sync
    google_event_id = models.CharField(max_length=200, blank=True)
    outlook_event_id = models.CharField(max_length=200, blank=True)

    # Assigned to team member
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="voice_appointments",
    )

    class Meta:
        db_table = "voice_agent_calendarevent"
        ordering = ["start_time"]
        indexes = [
            models.Index(fields=["website", "start_time"]),
            models.Index(fields=["website", "status"]),
        ]

    def __str__(self):
        return f"Appointment({self.attendee_name}, {self.start_time})"


class CallbackReminder(TimestampMixin):
    """Reminders to call back a contact."""

    STATUS_PENDING = "pending"
    STATUS_SENT = "sent"
    STATUS_COMPLETED = "completed"
    STATUS_DISMISSED = "dismissed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_SENT, "Sent"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_DISMISSED, "Dismissed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    website = models.ForeignKey(
        "websites.Website", on_delete=models.CASCADE, related_name="callback_reminders"
    )
    call_log = models.ForeignKey(
        CallLog, null=True, blank=True, on_delete=models.SET_NULL, related_name="callback_reminders"
    )
    contact_name = models.CharField(max_length=200)
    contact_phone = models.CharField(max_length=30)
    reason = models.TextField(blank=True)
    remind_at = models.DateTimeField(db_index=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="callback_reminders",
    )
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "voice_agent_callbackreminder"
        ordering = ["remind_at"]
        indexes = [
            models.Index(fields=["website", "status", "remind_at"]),
        ]

    def __str__(self):
        return f"Callback({self.contact_name}, {self.remind_at})"


class CallExtraction(TimestampMixin):
    """Structured data extracted from a call transcript by the self-hosted LLM."""

    call_log = models.OneToOneField(
        CallLog, on_delete=models.CASCADE, related_name="extraction"
    )
    caller_info = models.JSONField(
        default=dict,
        help_text='{"name": "", "phone": "", "email": "", "company": ""}',
    )
    call_summary = models.TextField(blank=True)
    call_category = models.CharField(
        max_length=30,
        blank=True,
        help_text="appointment, inquiry, complaint, support, sales, other",
    )
    sentiment = models.CharField(max_length=20, blank=True)
    follow_ups = models.JSONField(
        default=list,
        help_text='[{"description": "", "urgency": "immediate|within_24h|this_week|no_rush"}]',
    )
    appointments_detected = models.JSONField(
        default=list,
        help_text='[{"date": "", "time": "", "description": "", "confirmed": false}]',
    )
    raw_llm_output = models.JSONField(
        default=dict,
        help_text="Full JSON output from the extraction LLM for debugging.",
    )
    model_used = models.CharField(max_length=100, blank=True)
    processing_time_ms = models.IntegerField(default=0)

    class Meta:
        db_table = "voice_agent_callextraction"

    def __str__(self):
        return f"Extraction(call={self.call_log_id}, category={self.call_category})"


class CallTodo(TimestampMixin):
    """Action items extracted from a call — shown to the business owner."""

    PRIORITY_HIGH = "high"
    PRIORITY_MEDIUM = "medium"
    PRIORITY_LOW = "low"
    PRIORITY_CHOICES = [
        (PRIORITY_HIGH, "High"),
        (PRIORITY_MEDIUM, "Medium"),
        (PRIORITY_LOW, "Low"),
    ]

    STATUS_OPEN = "open"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_DONE = "done"
    STATUS_DISMISSED = "dismissed"
    STATUS_CHOICES = [
        (STATUS_OPEN, "Open"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_DONE, "Done"),
        (STATUS_DISMISSED, "Dismissed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    website = models.ForeignKey(
        "websites.Website", on_delete=models.CASCADE, related_name="call_todos"
    )
    call_log = models.ForeignKey(
        CallLog, on_delete=models.CASCADE, related_name="todos"
    )
    description = models.TextField()
    priority = models.CharField(
        max_length=10, choices=PRIORITY_CHOICES, default=PRIORITY_MEDIUM, db_index=True
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN, db_index=True
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="call_todos",
    )
    due_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "voice_agent_calltodo"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["website", "status"]),
            models.Index(fields=["website", "priority", "status"]),
        ]

    def __str__(self):
        return f"Todo({self.description[:50]}, {self.priority}, {self.status})"


class CallCampaign(TimestampMixin):
    """An outbound calling campaign. Targets are dialed by the AI voice agent
    using the website's merged knowledge-base prompt and a per-campaign welcome line."""

    STATUS_DRAFT = "draft"
    STATUS_RUNNING = "running"
    STATUS_PAUSED = "paused"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_RUNNING, "Running"),
        (STATUS_PAUSED, "Paused"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_FAILED, "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    website = models.ForeignKey(
        "websites.Website", on_delete=models.CASCADE, related_name="call_campaigns"
    )
    name = models.CharField(max_length=200)
    welcome_message = models.TextField(
        help_text="Opening line played to the recipient when they answer."
    )
    from_number = models.ForeignKey(
        PhoneNumber,
        on_delete=models.PROTECT,
        related_name="campaigns",
        help_text="Caller-ID this campaign dials out from. Must belong to the same website.",
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True
    )
    max_concurrent_calls = models.PositiveSmallIntegerField(default=3)
    calls_per_minute = models.PositiveSmallIntegerField(default=10)
    respect_business_hours = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="call_campaigns",
    )

    class Meta:
        db_table = "voice_agent_callcampaign"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["website", "status"]),
        ]

    def __str__(self):
        return f"Campaign({self.name}, {self.status})"


class CallTarget(TimestampMixin):
    """A single recipient inside a CallCampaign."""

    STATUS_PENDING = "pending"
    STATUS_QUEUED = "queued"
    STATUS_DIALING = "dialing"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_NO_ANSWER = "no_answer"
    STATUS_BUSY = "busy"
    STATUS_DO_NOT_CALL = "do_not_call"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_QUEUED, "Queued"),
        (STATUS_DIALING, "Dialing"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_FAILED, "Failed"),
        (STATUS_NO_ANSWER, "No Answer"),
        (STATUS_BUSY, "Busy"),
        (STATUS_DO_NOT_CALL, "Do Not Call"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(
        CallCampaign, on_delete=models.CASCADE, related_name="targets"
    )
    phone = models.CharField(max_length=30, db_index=True, help_text="E.164 format")
    name = models.CharField(max_length=200, blank=True)
    metadata = models.JSONField(
        default=dict, blank=True,
        help_text="Custom fields imported from CSV (e.g. company, product interest).",
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True
    )
    attempt_count = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=2)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)

    class Meta:
        db_table = "voice_agent_calltarget"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["campaign", "status"]),
        ]
        unique_together = [("campaign", "phone")]

    def __str__(self):
        return f"Target({self.phone}, {self.status})"


class DoNotCallEntry(TimestampMixin):
    """Global do-not-call list. Outbound dialer skips any phone present here."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone = models.CharField(max_length=30, unique=True, db_index=True)
    reason = models.CharField(max_length=200, blank=True)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dnc_entries",
    )

    class Meta:
        db_table = "voice_agent_donotcallentry"
        ordering = ["-created_at"]

    def __str__(self):
        return f"DNC({self.phone})"
