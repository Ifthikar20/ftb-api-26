"""Self-serve SMS subscription management.

The mobile-number lifecycle, driven from Settings:

    add number -> code texted -> verify (consent recorded) -> toggle
    alert flags -> opt out

Everything here is authenticated and scoped to ``request.user``; a
stranger's subscription id is indistinguishable from a missing one (404).
The low-level pieces -- normalization, the keyed phone digest, code
generation/verification and the Twilio transport -- live in
``sms_service`` and are reused, not reimplemented, so the digest written
here is the exact digest the inbound webhook matches on.

Two things never leave this module: the raw phone number (rows carry a
masked last-4 rendering only) and the verification code (it exists in the
outbound text and nowhere else -- not in responses, not in logs).
"""

from __future__ import annotations

from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from apps.notifications.models import SmsSubscription
from apps.notifications.services import sms_service
from core.exceptions import CanseeException
from core.interceptors.throttling import AuthRateThrottle, PasswordResetThrottle
from core.views import TenantScopedAPIView

INVALID_PHONE_MESSAGE = (
    "Enter a mobile number in international format (+14155551234)."
)
UNAVAILABLE_MESSAGE = "Text messaging isn't configured on this deployment."

# The four subscriber-editable flags. PATCH accepts exactly these, each
# handled explicitly -- no setattr from arbitrary request keys.
FLAG_FIELDS = (
    "alert_security",
    "alert_visibility_drop",
    "allow_replies",
    "pulse_digest",
)


def _masked_phone(phone_e164: str) -> str:
    """Render a number as its last four digits only.

    The stored number is encrypted PII; the UI needs just enough to tell
    two subscriptions apart. This is the single place a decrypted number
    is turned into display text, and it never includes more than four
    digits.
    """
    digits = "".join(c for c in (phone_e164 or "") if c.isdigit())
    return f"•••-•••-{digits[-4:]}"


def _row(subscription: SmsSubscription) -> dict:
    """The one client-facing shape for a subscription. Never the raw number."""
    return {
        "id": str(subscription.id),
        "phone_masked": _masked_phone(subscription.phone_e164),
        "status": subscription.status,
        "alert_security": subscription.alert_security,
        "alert_visibility_drop": subscription.alert_visibility_drop,
        "allow_replies": subscription.allow_replies,
        "pulse_digest": subscription.pulse_digest,
        "created_at": subscription.created_at,
    }


def _send_verification(subscription: SmsSubscription) -> bool:
    """Rotate the code, persist its hash, and text it out.

    Returns whether the send succeeded. The code itself is deliberately
    confined to this function's frame and the outbound SMS body.
    """
    code = sms_service.generate_code()
    subscription.verification_code_hash = sms_service.hash_code(code)
    subscription.verification_sent_at = timezone.now()
    subscription.verification_attempts = 0
    subscription.save(
        update_fields=[
            "status",
            "verification_code_hash",
            "verification_sent_at",
            "verification_attempts",
            "updated_at",
        ]
    )
    return sms_service.send_sms(
        subscription.phone_e164,
        f"Your Cansee verification code is {code}. It expires in 10 minutes.",
    )


class _SmsScopedView(TenantScopedAPIView):
    """Base: authenticated, with user-scoped row lookup (stranger id = 404)."""

    def get_subscription(self, pk) -> SmsSubscription:
        return self.get_tenant_object(
            SmsSubscription.objects.filter(user=self.request.user), id=pk
        )


class SmsSubscriptionListView(_SmsScopedView):
    """GET  /api/v1/notifications/sms/  -- list the user's numbers.
    POST /api/v1/notifications/sms/  -- add a number and text a code.
    """

    def get_throttles(self):
        # Adding a number sends a real SMS, so it shares the tight
        # password-reset budget; listing stays on the default throttles.
        if self.request.method == "POST":
            return [PasswordResetThrottle()]
        return super().get_throttles()

    def get(self, request):
        subscriptions = SmsSubscription.objects.filter(user=request.user)
        return Response(
            {
                "available": sms_service.is_enabled(),
                "subscriptions": [_row(s) for s in subscriptions],
            }
        )

    def post(self, request):
        phone = sms_service.normalize_phone(str(request.data.get("phone", "") or ""))
        if not phone or not sms_service.looks_like_phone(phone):
            raise CanseeException(INVALID_PHONE_MESSAGE, code="validation_error")
        if not sms_service.is_enabled():
            raise CanseeException(
                UNAVAILABLE_MESSAGE, code="sms_unavailable", status_code=503
            )

        # Same digest function the inbound webhook matches on -- the two
        # sides must agree or replies stop finding their subscription.
        subscription, created = SmsSubscription.objects.get_or_create(
            user=request.user,
            phone_hash=sms_service.hash_phone(phone),
            defaults={"phone_e164": phone},
        )
        if not created and subscription.status == SmsSubscription.Status.VERIFIED:
            raise CanseeException(
                "This number is already verified.", code="already_verified"
            )

        # An opted-out row revives to pending rather than erroring: the
        # user is allowed to change their mind. If the opt-out came from a
        # carrier STOP, Twilio blocks sends to the number anyway, so
        # re-verification cannot be used to text an unwilling recipient.
        # (An existing pending row just gets a fresh code -- same effect
        # as a resend.)
        subscription.status = SmsSubscription.Status.PENDING

        sent = _send_verification(subscription)
        return Response(
            {**_row(subscription), "sent": sent},
            status=status.HTTP_201_CREATED,
        )


class SmsVerifyView(_SmsScopedView):
    """POST /api/v1/notifications/sms/<id>/verify/ -- prove number ownership."""

    throttle_classes = [AuthRateThrottle]

    def post(self, request, pk):
        subscription = self.get_subscription(pk)
        if subscription.status == SmsSubscription.Status.VERIFIED:
            raise CanseeException(
                "This number is already verified.", code="already_verified"
            )

        code = str(request.data.get("code", "") or "").strip()
        if sms_service.code_matches(subscription, code):
            subscription.status = SmsSubscription.Status.VERIFIED
            # The consent record (TCPA): who agreed, when, from where.
            subscription.consented_at = timezone.now()
            subscription.consent_ip = request.META.get("REMOTE_ADDR", "") or None
            # A revived number's new consent supersedes the old opt-out.
            subscription.opted_out_at = None
            # The code is spent; keeping its hash around serves nothing.
            subscription.verification_code_hash = ""
            subscription.save(
                update_fields=[
                    "status",
                    "consented_at",
                    "consent_ip",
                    "opted_out_at",
                    "verification_code_hash",
                    "updated_at",
                ]
            )
            return Response(_row(subscription))

        # Distinguish "this code can never match again" (expired, attempts
        # spent, or no code outstanding) from a plain wrong guess, so the
        # UI knows whether to offer the field again or a resend button.
        dead = (
            not subscription.verification_code_hash
            or not subscription.verification_sent_at
            or subscription.verification_attempts
            >= sms_service.MAX_VERIFICATION_ATTEMPTS
            or (timezone.now() - subscription.verification_sent_at).total_seconds()
            > sms_service.VERIFICATION_TTL_SECONDS
        )
        if dead:
            raise CanseeException(
                "That code has expired. Request a new code.", code="code_expired"
            )

        subscription.verification_attempts += 1
        subscription.save(update_fields=["verification_attempts", "updated_at"])
        remaining = (
            sms_service.MAX_VERIFICATION_ATTEMPTS
            - subscription.verification_attempts
        )
        raise CanseeException(
            f"That code didn't match. {remaining} attempts left.",
            code="invalid_code",
        )


class SmsResendView(_SmsScopedView):
    """POST /api/v1/notifications/sms/<id>/resend/ -- fresh code to a pending row."""

    throttle_classes = [PasswordResetThrottle]

    def post(self, request, pk):
        subscription = self.get_subscription(pk)
        if subscription.status == SmsSubscription.Status.VERIFIED:
            raise CanseeException(
                "This number is already verified.", code="already_verified"
            )
        if subscription.status == SmsSubscription.Status.OPTED_OUT:
            # Reviving an opted-out number is an explicit re-add (POST /sms/),
            # not a side effect of mashing resend.
            raise CanseeException(
                "This number has opted out. Add it again to re-verify.",
                code="opted_out",
            )
        sent = _send_verification(subscription)
        return Response({"ok": True, "sent": sent})


class SmsSubscriptionDetailView(_SmsScopedView):
    """PATCH  /api/v1/notifications/sms/<id>/ -- toggle alert flags.
    DELETE /api/v1/notifications/sms/<id>/ -- opt the number out.
    """

    def patch(self, request, pk):
        subscription = self.get_subscription(pk)
        if subscription.status != SmsSubscription.Status.VERIFIED:
            raise CanseeException(
                "Verify this number before changing its alerts.",
                code="not_verified",
            )

        changed: list[str] = []
        for field in FLAG_FIELDS:
            if field not in request.data:
                continue
            value = request.data.get(field)
            if not isinstance(value, bool):
                raise CanseeException(
                    f"{field} must be true or false.", code="validation_error"
                )
            setattr(subscription, field, value)
            changed.append(field)
        if not changed:
            raise CanseeException("Nothing to update.", code="validation_error")

        subscription.save(update_fields=[*changed, "updated_at"])
        return Response(_row(subscription))

    def delete(self, request, pk):
        subscription = self.get_subscription(pk)
        # Soft opt-out, never a hard delete: the row IS the consent record
        # (who agreed, when, from which IP, and when they left), and that
        # history is what answers a TCPA complaint or a regulator's
        # question. Deleting it would destroy the very evidence that the
        # sends before the opt-out were lawful.
        if subscription.status != SmsSubscription.Status.OPTED_OUT:
            subscription.status = SmsSubscription.Status.OPTED_OUT
            subscription.opted_out_at = timezone.now()
            subscription.save(
                update_fields=["status", "opted_out_at", "updated_at"]
            )
        return Response({"ok": True})
