"""Lightweight User-Agent parser — no external dependencies."""


# Substrings that mark a request as automated. Covers generic crawler
# markers plus the named bots that dominate web logs: search engines, SEO
# tools, AI/LLM crawlers, social-unfurl fetchers, uptime monitors, and
# headless browsers. Matched case-insensitively as a substring of the UA.
# Kept deliberately broad — a real browser never contains these tokens, so
# false positives are near-zero, and every match we drop is traffic that
# would otherwise inflate every analytics metric.
BOT_MARKERS = (
    # generic automation
    "bot", "crawler", "spider", "slurp", "wget", "curl", "python-requests",
    "httpclient", "go-http", "okhttp", "headless", "phantomjs", "puppeteer",
    "playwright", "scrapy", "libwww", "lighthouse",
    # search engines
    "googlebot", "bingbot", "yandexbot", "duckduckbot", "baiduspider",
    "applebot", "petalbot",
    # AI / LLM crawlers
    "gptbot", "oai-searchbot", "chatgpt-user", "claudebot", "claude-web",
    "anthropic-ai", "perplexitybot", "perplexity-user", "ccbot",
    "google-extended", "bytespider", "amazonbot", "youbot", "cohere-ai",
    "diffbot", "meta-externalagent",
    # SEO / marketing tools
    "ahrefsbot", "semrushbot", "mj12bot", "dotbot", "rogerbot",
    "screaming frog", "sitebulb", "dataforseo",
    # social unfurlers / link previews
    "facebookexternalhit", "twitterbot", "linkedinbot", "slackbot",
    "discordbot", "telegrambot", "whatsapp", "embedly", "pinterest",
    # uptime / monitoring
    "uptimerobot", "pingdom", "statuscake", "site24x7", "datadog",
    "gtmetrix", "google-pagespeed",
)


def is_bot(ua: str) -> bool:
    """Return True if the user-agent looks like an automated client.

    A blank UA is treated as a bot: every real browser sends one, so a
    missing UA is itself a strong automation signal and dropping it keeps
    blank-UA floods out of the metrics.
    """
    if not ua:
        return True
    ua_lower = ua.lower()
    return any(marker in ua_lower for marker in BOT_MARKERS)


def parse_user_agent(ua: str) -> dict:
    """Parse a user-agent string into device_type, browser, and os."""
    if not ua:
        return {"device_type": "unknown", "browser": "unknown", "os": "unknown"}

    ua_lower = ua.lower()

    # ── Device type ──
    if is_bot(ua):
        device_type = "bot"
    elif any(k in ua_lower for k in ("mobile", "android", "iphone", "ipod")):
        device_type = "mobile"
    elif any(k in ua_lower for k in ("ipad", "tablet")):
        device_type = "tablet"
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

    # ── OS ── (order matters: iOS before macOS since iPhone UA contains 'Mac OS')
    os_name = "other"
    if "iphone" in ua_lower or "ipad" in ua_lower:
        os_name = "iOS"
    elif "android" in ua_lower:
        os_name = "Android"
    elif "windows" in ua_lower:
        os_name = "Windows"
    elif "mac os" in ua_lower or "macintosh" in ua_lower:
        os_name = "macOS"
    elif "cros" in ua_lower:
        os_name = "ChromeOS"
    elif "linux" in ua_lower:
        os_name = "Linux"

    return {"device_type": device_type, "browser": browser, "os": os_name}


def get_client_ip(request) -> str:
    """Extract the real client IP from the request, proxy-aware.

    X-Forwarded-For is appended-to by each hop, so the left-most entry is
    whatever the *client* claimed and is freely spoofable. We trust the
    last ``settings.TRUSTED_PROXY_COUNT`` hops (our own load balancer /
    nginx) and take the entry just before them. Defaults to one trusted
    proxy, which matches the standard single-nginx prod topology.
    """
    from django.conf import settings

    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        parts = [p.strip() for p in xff.split(",") if p.strip()]
        if parts:
            trusted = max(1, int(getattr(settings, "TRUSTED_PROXY_COUNT", 1)))
            # The right-most `trusted` entries were added by our infra. The
            # entry immediately to their left is the real client.
            idx = len(parts) - trusted - 1
            if idx < 0:
                idx = 0
            return parts[idx]
    return request.META.get("REMOTE_ADDR", "")
