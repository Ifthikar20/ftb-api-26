"""Small helpers shared by agents."""
from __future__ import annotations

from urllib.parse import urlparse

from apps.brand_vault.models import BrandSecurityConfig


def brand_terms(website, config: dict) -> list[str]:
    """Resolve the list of brand terms to monitor.

    Preference order: agent-config override -> per-website BrandSecurityConfig
    row -> the website's ``name`` -> the URL's domain root. Empty strings
    filtered out.
    """
    override = config.get("brand_terms") or []
    if isinstance(override, list) and override:
        return [t for t in (str(x).strip() for x in override) if t]

    try:
        cfg = website.security_config
        if cfg and cfg.brand_terms:
            return [t for t in (str(x).strip() for x in cfg.brand_terms) if t]
    except BrandSecurityConfig.DoesNotExist:
        pass
    except Exception:
        pass

    if website.name:
        return [website.name.strip()]
    if website.url:
        host = urlparse(website.url).netloc or website.url
        host = host.split(":", 1)[0]
        if host.startswith("www."):
            host = host[4:]
        root = host.split(".")[0] if "." in host else host
        return [root] if root else []
    return []


def negative_keywords(website, config: dict) -> list[str]:
    """Resolve the negative-keyword list used to modify brand queries."""
    override = config.get("negative_keywords") or []
    if isinstance(override, list) and override:
        return [t for t in (str(x).strip() for x in override) if t]
    try:
        cfg = website.security_config
        if cfg and cfg.negative_keywords:
            return [t for t in (str(x).strip() for x in cfg.negative_keywords) if t]
    except BrandSecurityConfig.DoesNotExist:
        pass
    except Exception:
        pass
    return ["scam", "lawsuit", "complaint", "fraud", "review", "alternative"]


def website_domain(website) -> str:
    """Extract the host portion of the website URL (no scheme, no path)."""
    if not website.url:
        return ""
    host = urlparse(website.url).netloc or website.url
    host = host.split(":", 1)[0]
    if host.startswith("www."):
        host = host[4:]
    return host


