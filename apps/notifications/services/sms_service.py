"""SMS channel (Twilio).

The most intrusive channel in the product, so it is the most tightly
gated: nothing sends unless SMS_ENABLED is on, credentials exist, the
number is verified, and the subscription has not opted out. Every one of
those is checked at send time rather than trusted from the caller.

Compliance is not decoration here. US A2P texting requires prior express
consent, an honoured STOP, and a HELP response. Those live in
`handle_keyword` and are checked before anything else an inbound message
might mean -- a person texting STOP must be unsubscribed even if the rest
of the pipeline is broken.

No Twilio SDK dependency: the REST API is one form POST, and the webhook
signature is documented HMAC. Adding a package for that is not worth it.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import secrets

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger("apps")

API_ROOT = "https://api.twilio.com/2010-04-01"
SEND_TIMEOUT = 10.0

# A single segment is 160 GSM-7 characters; past that Twilio bills per
# segment and long texts arrive split and reordered on some carriers.
# Two segments is the practical ceiling for something readable.
MAX_BODY_CHARS = 300

VERIFICATION_TTL_SECONDS = 10 * 60
MAX_VERIFICATION_ATTEMPTS = 5

# Carrier-mandated keywords. Matched case-insensitively on the whole body.
STOP_WORDS = {"stop", "stopall", "unsubscribe", "cancel", "end", "quit"}
START_WORDS = {"start", "unstop", "yes"}
HELP_WORDS = {"help", "info"}

HELP_REPLY = (
    "Cansee alerts. Reply STOP to unsubscribe, START to resume. "
    "Ask a question in plain English and I'll answer from your account data. "
    "Msg&data rates may apply."
)
STOP_REPLY = "You're unsubscribed from Cansee texts. Reply START to resume."
START_REPLY = "You're resubscribed to Cansee alerts. Reply STOP to unsubscribe."


def is_configured() -> bool:
    return bool(
        getattr(settings, "TWILIO_ACCOUNT_SID", "")
        and getattr(settings, "TWILIO_AUTH_TOKEN", "")
        and getattr(settings, "TWILIO_FROM_NUMBER", "")
    )


def is_enabled() -> bool:
    """Deployment switch, checked before credentials so the feature can be
    turned off without pulling secrets."""
    return bool(getattr(settings, "SMS_ENABLED", False)) and is_configured()


def hash_phone(phone_e164: str) -> str:
    """Lookup digest for an encrypted number.

    Keyed with the app secret so the digest is not a plain SHA of a
    guessable value -- the phone-number space is small enough to enumerate
    against an unkeyed hash.
    """
    key = (getattr(settings, "SECRET_KEY", "") or "").encode()
    return hmac.new(key, normalize_phone(phone_e164).encode(), hashlib.sha256).hexdigest()


def normalize_phone(raw: str) -> str:
    """Reduce to E.164-ish: a leading + and digits only.

    Deliberately not a full phone-number parser. Twilio rejects malformed
    numbers at send time with a clear error, and carrying libphonenumber
    for a settings field is not worth the weight.
    """
    text = (raw or "").strip()
    digits = "".join(c for c in text if c.isdigit())
    if not digits:
        return ""
    return f"+{digits}"


def looks_like_phone(raw: str) -> bool:
    digits = "".join(c for c in (raw or "") if c.isdigit())
    # E.164 allows 15 digits max; anything under 8 is not a mobile number.
    return 8 <= len(digits) <= 15


# -- verification --------------------------------------------------------


def generate_code() -> str:
    """A 6-digit code from a CSPRNG."""
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_code(code: str) -> str:
    key = (getattr(settings, "SECRET_KEY", "") or "").encode()
    return hmac.new(key, (code or "").strip().encode(), hashlib.sha256).hexdigest()


def code_matches(subscription, code: str) -> bool:
    """Constant-time compare, with expiry and attempt ceiling enforced."""
    if not subscription.verification_code_hash or not subscription.verification_sent_at:
        return False
    if subscription.verification_attempts >= MAX_VERIFICATION_ATTEMPTS:
        return False
    age = (timezone.now() - subscription.verification_sent_at).total_seconds()
    if age > VERIFICATION_TTL_SECONDS:
        return False
    return hmac.compare_digest(subscription.verification_code_hash, hash_code(code))


# -- outbound ------------------------------------------------------------


def send_sms(to_e164: str, body: str) -> bool:
    """Send one message. Returns False rather than raising: a failed alert
    must not take down the scan or webhook that triggered it."""
    if not is_enabled():
        logger.info("sms: skipped, channel disabled or unconfigured")
        return False
    to = normalize_phone(to_e164)
    if not looks_like_phone(to):
        logger.warning("sms: refusing to send to a malformed number")
        return False

    try:
        import requests
    except ImportError:  # pragma: no cover - requests is a hard dependency
        return False

    sid = settings.TWILIO_ACCOUNT_SID
    payload = {
        "To": to,
        "From": settings.TWILIO_FROM_NUMBER,
        "Body": (body or "")[:MAX_BODY_CHARS],
    }
    try:
        resp = requests.post(
            f"{API_ROOT}/Accounts/{sid}/Messages.json",
            data=payload,
            auth=(sid, settings.TWILIO_AUTH_TOKEN),
            timeout=SEND_TIMEOUT,
        )
    except Exception as exc:
        logger.warning("sms: send failed: %s", exc)
        return False

    if resp.status_code >= 300:
        # Never log the body: it contains the recipient number.
        logger.warning("sms: twilio returned HTTP %s", resp.status_code)
        return False
    return True


def notify(subscription, body: str) -> bool:
    """Send to a subscription, honouring its state. The only path alerts
    should use -- it is what makes an opt-out actually stick."""
    if subscription is None or not subscription.is_active:
        return False
    sent = send_sms(subscription.phone_e164, body)
    if sent:
        subscription.last_message_at = timezone.now()
        subscription.save(update_fields=["last_message_at", "updated_at"])
    return sent


# -- inbound -------------------------------------------------------------


def verify_twilio_signature(request) -> bool:
    """Validate X-Twilio-Signature.

    Twilio signs the full URL plus the POST fields sorted by key, HMAC-SHA1
    with the auth token, base64 encoded. Without this the webhook is an
    open endpoint anyone can post to and impersonate a subscriber.
    """
    token = (getattr(settings, "TWILIO_AUTH_TOKEN", "") or "").encode()
    if not token:
        return False
    signature = request.headers.get("X-Twilio-Signature", "")
    if not signature:
        return False

    # Twilio signs the URL it was configured with. Behind nginx/Cloudflare
    # the reconstructed scheme can differ, so allow an explicit override.
    url = getattr(settings, "TWILIO_WEBHOOK_URL", "") or request.build_absolute_uri()
    payload = url + "".join(
        f"{k}{v}" for k, v in sorted(request.POST.items())
    )
    expected = base64.b64encode(
        hmac.new(token, payload.encode("utf-8"), hashlib.sha1).digest()
    ).decode()
    return hmac.compare_digest(expected, signature)


def handle_keyword(subscription, body: str) -> str | None:
    """Apply STOP / START / HELP. Returns the reply, or None if the message
    was not a keyword and should be treated as a question.

    Checked before any other interpretation: an opt-out has to work even
    when everything downstream is failing.
    """
    word = (body or "").strip().lower()
    if word in STOP_WORDS:
        if subscription is not None:
            subscription.status = subscription.Status.OPTED_OUT
            subscription.opted_out_at = timezone.now()
            subscription.save(update_fields=["status", "opted_out_at", "updated_at"])
        return STOP_REPLY
    if word in START_WORDS:
        if subscription is not None and subscription.status == subscription.Status.OPTED_OUT:
            subscription.status = subscription.Status.VERIFIED
            subscription.opted_out_at = None
            subscription.save(update_fields=["status", "opted_out_at", "updated_at"])
        return START_REPLY
    if word in HELP_WORDS:
        return HELP_REPLY
    return None


def twiml(message: str = "") -> str:
    """Minimal TwiML. An empty <Response/> tells Twilio to send nothing."""
    if not message:
        return "<?xml version='1.0' encoding='UTF-8'?><Response/>"
    safe = (
        str(message)[:MAX_BODY_CHARS]
        .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )
    return f"<?xml version='1.0' encoding='UTF-8'?><Response><Message>{safe}</Message></Response>"
