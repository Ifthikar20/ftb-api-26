import re
from urllib.parse import urlparse

from django.core.exceptions import ValidationError


def validate_website_url(url: str) -> str:
    """Validate that a URL is a proper, publicly reachable website URL."""
    if not url:
        raise ValidationError("URL is required.")

    # Normalize — add https if missing
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    try:
        parsed = urlparse(url)
    except Exception:
        raise ValidationError("Invalid URL format.")

    if not parsed.netloc:
        raise ValidationError("URL must include a domain.")

    # Block localhost and private IPs
    private_patterns = [
        r"^localhost",
        r"^127\.",
        r"^10\.",
        r"^192\.168\.",
        r"^172\.(1[6-9]|2\d|3[01])\.",
    ]
    if any(re.match(p, parsed.netloc) for p in private_patterns):
        raise ValidationError("URL must be a publicly reachable domain.")

    return url
