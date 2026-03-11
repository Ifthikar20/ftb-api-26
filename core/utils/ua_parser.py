"""Lightweight User-Agent parser — no external dependencies."""

import re


def parse_user_agent(ua: str) -> dict:
    """Parse a user-agent string into device_type, browser, and os."""
    if not ua:
        return {"device_type": "unknown", "browser": "unknown", "os": "unknown"}

    ua_lower = ua.lower()

    # ── Device type ──
    if any(k in ua_lower for k in ("mobile", "android", "iphone", "ipod")):
        device_type = "mobile"
    elif any(k in ua_lower for k in ("ipad", "tablet")):
        device_type = "tablet"
    elif any(k in ua_lower for k in ("bot", "crawler", "spider", "slurp", "wget", "curl")):
        device_type = "bot"
    else:
        device_type = "desktop"

    # ── Browser ──
    browser = "other"
    if "edg" in ua_lower:
        browser = "Edge"
    elif "opr" in ua_lower or "opera" in ua_lower:
        browser = "Opera"
    elif "chrome" in ua_lower and "safari" in ua_lower:
        browser = "Chrome"
    elif "firefox" in ua_lower:
        browser = "Firefox"
    elif "safari" in ua_lower:
        browser = "Safari"
    elif "msie" in ua_lower or "trident" in ua_lower:
        browser = "IE"

    # ── OS ──
    os_name = "other"
    if "windows" in ua_lower:
        os_name = "Windows"
    elif "mac os" in ua_lower or "macintosh" in ua_lower:
        os_name = "macOS"
    elif "iphone" in ua_lower or "ipad" in ua_lower:
        os_name = "iOS"
    elif "android" in ua_lower:
        os_name = "Android"
    elif "linux" in ua_lower:
        os_name = "Linux"
    elif "cros" in ua_lower:
        os_name = "ChromeOS"

    return {"device_type": device_type, "browser": browser, "os": os_name}


def get_client_ip(request) -> str:
    """Extract the real client IP from the request (handles proxies)."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")
