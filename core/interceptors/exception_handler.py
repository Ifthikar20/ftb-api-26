import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError as DjangoValidationError
from core.exceptions import GrowthPilotException

logger = logging.getLogger("apps")


def custom_exception_handler(exc, context):
    """
    Wraps ALL API errors in a consistent envelope:
    {
        "success": false,
        "error": {
            "code": "error_code",
            "message": "Human-readable message",
            "details": { ... }
        },
        "request_id": "uuid"
    }
    """
    request = context.get("request")
    request_id = getattr(request, "request_id", "unknown") if request else "unknown"

    # Handle our domain exceptions
    if isinstance(exc, GrowthPilotException):
        return Response(
            {
                "success": False,
                "error": {"code": exc.code, "message": exc.message},
                "request_id": request_id,
            },
            status=exc.status_code,
        )

    # Handle Django validation errors
    if isinstance(exc, DjangoValidationError):
        return Response(
            {
                "success": False,
                "error": {
                    "code": "validation_error",
                    "message": "Validation failed.",
                    "details": (
                        exc.message_dict
                        if hasattr(exc, "message_dict")
                        else {"non_field_errors": exc.messages}
                    ),
                },
                "request_id": request_id,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Let DRF handle its own exceptions
    response = exception_handler(exc, context)

    if response is not None:
        error_data = response.data
        message = "An error occurred."

        if isinstance(error_data, dict):
            message = error_data.get("detail", str(error_data))
        elif isinstance(error_data, list):
            message = error_data[0] if error_data else message

        response.data = {
            "success": False,
            "error": {"code": "api_error", "message": str(message), "details": error_data},
            "request_id": request_id,
        }
        return response

    # Unhandled exceptions
    logger.exception(f"Unhandled exception: {exc}", extra={"request_id": request_id})

    return Response(
        {
            "success": False,
            "error": {
                "code": "internal_error",
                "message": "An unexpected error occurred. Our team has been notified.",
            },
            "request_id": request_id,
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
