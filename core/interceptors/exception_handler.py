import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError as DjangoValidationError
from core.exceptions import GrowthPilotException

logger = logging.getLogger("apps")

# ──────────────────────────────────────────────────
# User-friendly messages — NEVER expose raw errors
# ──────────────────────────────────────────────────

FRIENDLY_MESSAGES = {
    400: "We couldn't process that request. Please check your input and try again.",
    401: "Your session has expired. Please log in again.",
    403: "You don't have permission to do that.",
    404: "We couldn't find what you're looking for.",
    405: "That action isn't supported.",
    409: "There's a conflict with your request. Please try again.",
    429: "You're making too many requests. Please wait a moment and try again.",
    500: "Something went wrong on our end. We've been notified and are looking into it.",
    502: "Our servers are temporarily unavailable. Please try again in a moment.",
    503: "This service is temporarily unavailable. Please try again shortly.",
}


def _friendly_message(status_code: int, fallback: str = "") -> str:
    """Return a calm, user-friendly message. Never expose raw errors."""
    return FRIENDLY_MESSAGES.get(status_code, fallback or FRIENDLY_MESSAGES[500])


def custom_exception_handler(exc, context):
    """
    Wraps ALL API errors in a consistent envelope with user-friendly messages.
    Raw exception details are logged server-side but NEVER sent to the client.

    Response format:
    {
        "success": false,
        "error": {
            "code": "error_code",
            "message": "Calm, user-friendly message"
        },
        "request_id": "uuid"
    }
    """
    request = context.get("request")
    request_id = getattr(request, "request_id", "unknown") if request else "unknown"

    # ── Our domain exceptions (already have safe messages) ──
    if isinstance(exc, GrowthPilotException):
        return Response(
            {
                "success": False,
                "error": {"code": exc.code, "message": exc.message},
                "request_id": request_id,
            },
            status=exc.status_code,
        )

    # ── Django validation errors — show field-level feedback, not raw text ──
    if isinstance(exc, DjangoValidationError):
        return Response(
            {
                "success": False,
                "error": {
                    "code": "validation_error",
                    "message": "Please check your input and try again.",
                    "fields": (
                        exc.message_dict
                        if hasattr(exc, "message_dict")
                        else {"general": exc.messages}
                    ),
                },
                "request_id": request_id,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ── ValueError — log it, but NEVER expose str(exc) to users ──
    if isinstance(exc, ValueError):
        logger.warning(
            f"Business logic error: {exc}",
            extra={"request_id": request_id},
        )
        return Response(
            {
                "success": False,
                "error": {
                    "code": "validation_error",
                    "message": _friendly_message(400),
                },
                "request_id": request_id,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ── Let DRF handle its own exceptions ──
    response = exception_handler(exc, context)

    if response is not None:
        # Log the original error details server-side
        logger.warning(
            f"DRF exception ({response.status_code}): {response.data}",
            extra={"request_id": request_id},
        )

        # Replace the response data with a friendly message
        error_code = "api_error"
        if response.status_code == 401:
            error_code = "authentication_required"
        elif response.status_code == 403:
            error_code = "permission_denied"
        elif response.status_code == 404:
            error_code = "not_found"
        elif response.status_code == 429:
            error_code = "rate_limited"

        response.data = {
            "success": False,
            "error": {
                "code": error_code,
                "message": _friendly_message(response.status_code),
            },
            "request_id": request_id,
        }
        return response

    # ── Unhandled exceptions — log full stack, return calming message ──
    logger.exception(
        f"Unhandled exception: {exc.__class__.__name__}",
        extra={"request_id": request_id, "exception_type": type(exc).__name__},
    )

    return Response(
        {
            "success": False,
            "error": {
                "code": "internal_error",
                "message": _friendly_message(500),
            },
            "request_id": request_id,
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
