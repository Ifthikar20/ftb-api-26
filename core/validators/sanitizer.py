import re
import html


def strip_html_tags(text: str) -> str:
    """Remove all HTML tags from a string."""
    if not text:
        return text
    clean = re.compile(r"<[^>]+>")
    return html.unescape(clean.sub("", text))


def sanitize_text(text: str, max_length: int = None) -> str:
    """Strip HTML, normalize whitespace, and optionally truncate."""
    if not text:
        return text
    text = strip_html_tags(text)
    text = " ".join(text.split())
    if max_length:
        text = text[:max_length]
    return text
