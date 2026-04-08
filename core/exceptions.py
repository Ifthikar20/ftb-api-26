class GrowthPilotException(Exception):
    """Base exception for all domain errors."""

    def __init__(self, message: str, code: str = "error", status_code: int = 400):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class PlanLimitExceeded(GrowthPilotException):
    def __init__(self, message="You've reached your plan limit."):
        super().__init__(message, code="plan_limit_exceeded", status_code=403)


class ResourceNotFound(GrowthPilotException):
    def __init__(self, message="Resource not found."):
        super().__init__(message, code="not_found", status_code=404)


class PixelNotVerified(GrowthPilotException):
    def __init__(self):
        super().__init__(
            "Tracking pixel is not yet verified.", code="pixel_not_verified"
        )


class AuditInProgress(GrowthPilotException):
    def __init__(self):
        super().__init__("An audit is already running.", code="audit_in_progress")


class AIGenerationFailed(GrowthPilotException):
    def __init__(self):
        super().__init__(
            "AI generation failed. Please try again.",
            code="ai_failed",
            status_code=503,
        )


class CompetitorLimitReached(GrowthPilotException):
    def __init__(self):
        super().__init__(
            "Competitor tracking limit reached for your plan.",
            code="competitor_limit",
        )


class InvalidWebsiteURL(GrowthPilotException):
    def __init__(self):
        super().__init__(
            "The provided URL is not a valid, reachable website.",
            code="invalid_url",
        )


class PermissionDenied(GrowthPilotException):
    def __init__(self, message="You do not have permission to perform this action."):
        super().__init__(message, code="permission_denied", status_code=403)


class WebsiteNotFound(ResourceNotFound):
    def __init__(self):
        super().__init__("Website not found.")


class LeadNotFound(ResourceNotFound):
    def __init__(self):
        super().__init__("Lead not found.")


class DomainOwnershipRequired(GrowthPilotException):
    def __init__(self):
        super().__init__(
            "You can only run services on websites you own. Please verify ownership first.",
            code="domain_ownership_required",
            status_code=403,
        )


class RateLimited(GrowthPilotException):
    def __init__(self):
        super().__init__(
            "You're making requests too quickly. Please wait a moment and try again.",
            code="rate_limited",
            status_code=429,
        )


class SuspiciousInput(GrowthPilotException):
    def __init__(self):
        super().__init__(
            "Your request was blocked for security reasons.",
            code="suspicious_input",
            status_code=400,
        )

