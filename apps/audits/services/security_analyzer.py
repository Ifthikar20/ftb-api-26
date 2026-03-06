import logging
import ssl
import socket
from urllib.parse import urlparse
import requests
from apps.audits.models import Audit, AuditIssue

logger = logging.getLogger("apps")


class SecurityAnalyzer:
    """Security analysis: HTTPS, headers, mixed content, SSL certificate."""

    @staticmethod
    def analyze(*, website, audit: Audit) -> dict:
        score = 100
        url = website.url
        parsed = urlparse(url)

        try:
            response = requests.get(url, timeout=20, headers={
                "User-Agent": "FetchBot-Audit/1.0 (Security Analyzer)"
            })
            headers = response.headers
            content = response.text.lower()

            # ── HTTPS ──
            if not url.startswith("https://"):
                score -= 25
                AuditIssue.objects.create(
                    audit=audit, category="security", severity="critical",
                    title="Site not using HTTPS",
                    description="Your site is served over HTTP. All data is transmitted unencrypted.",
                    recommendation="Install an SSL certificate (free via Let's Encrypt) and redirect all HTTP to HTTPS.",
                    impact_score=25,
                )
            else:
                # ── SSL Certificate Check ──
                try:
                    hostname = parsed.hostname
                    ctx = ssl.create_default_context()
                    with socket.create_connection((hostname, 443), timeout=10) as sock:
                        with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                            cert = ssock.getpeercert()
                            import datetime
                            expiry = datetime.datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
                            days_left = (expiry - datetime.datetime.utcnow()).days
                            if days_left < 14:
                                score -= 15
                                AuditIssue.objects.create(
                                    audit=audit, category="security", severity="critical",
                                    title=f"SSL certificate expires in {days_left} days",
                                    description=f"Certificate expires on {expiry.strftime('%b %d, %Y')}. Expired certs cause browser warnings.",
                                    recommendation="Renew your SSL certificate immediately. Consider auto-renewal with Let's Encrypt.",
                                    impact_score=15,
                                )
                            elif days_left < 30:
                                score -= 5
                                AuditIssue.objects.create(
                                    audit=audit, category="security", severity="warning",
                                    title=f"SSL certificate expires in {days_left} days",
                                    description=f"Certificate expires on {expiry.strftime('%b %d, %Y')}.",
                                    recommendation="Renew your SSL certificate soon. Set up auto-renewal.",
                                    impact_score=5,
                                )
                except Exception as e:
                    logger.warning(f"SSL check failed for {url}: {e}")

            # ── Security Headers ──
            security_headers = {
                "Strict-Transport-Security": {
                    "title": "Missing HSTS header",
                    "desc": "HSTS tells browsers to always use HTTPS, preventing downgrade attacks.",
                    "rec": "Add 'Strict-Transport-Security: max-age=31536000; includeSubDomains' header.",
                    "penalty": 8,
                },
                "X-Content-Type-Options": {
                    "title": "Missing X-Content-Type-Options header",
                    "desc": "Without this header, browsers may MIME-sniff responses, enabling XSS attacks.",
                    "rec": "Add 'X-Content-Type-Options: nosniff' header.",
                    "penalty": 5,
                },
                "X-Frame-Options": {
                    "title": "Missing X-Frame-Options header",
                    "desc": "Without this header, your site can be embedded in iframes (clickjacking risk).",
                    "rec": "Add 'X-Frame-Options: DENY' or 'SAMEORIGIN' header.",
                    "penalty": 5,
                },
                "Content-Security-Policy": {
                    "title": "Missing Content-Security-Policy (CSP)",
                    "desc": "CSP prevents XSS and data injection attacks by whitelisting content sources.",
                    "rec": "Implement a Content-Security-Policy header. Start with 'default-src self'.",
                    "penalty": 8,
                },
                "X-XSS-Protection": {
                    "title": "Missing X-XSS-Protection header",
                    "desc": "This header enables the browser's built-in XSS filter.",
                    "rec": "Add 'X-XSS-Protection: 1; mode=block' header.",
                    "penalty": 3,
                },
                "Referrer-Policy": {
                    "title": "Missing Referrer-Policy header",
                    "desc": "Controls how much referrer info is sent with requests, protecting user privacy.",
                    "rec": "Add 'Referrer-Policy: strict-origin-when-cross-origin' header.",
                    "penalty": 3,
                },
                "Permissions-Policy": {
                    "title": "Missing Permissions-Policy header",
                    "desc": "Controls which browser features (camera, mic, geolocation) your site can use.",
                    "rec": "Add Permissions-Policy header to restrict unnecessary browser features.",
                    "penalty": 3,
                },
            }

            for header_name, info in security_headers.items():
                if header_name not in headers:
                    score -= info["penalty"]
                    AuditIssue.objects.create(
                        audit=audit, category="security",
                        severity="warning" if info["penalty"] >= 5 else "info",
                        title=info["title"],
                        description=info["desc"],
                        recommendation=info["rec"],
                        impact_score=info["penalty"],
                    )

            # ── Mixed Content ──
            if url.startswith("https://"):
                if "http://" in content and "https://" in content:
                    # Check for actual mixed content (HTTP resources on HTTPS page)
                    import re
                    http_resources = re.findall(r'(?:src|href|action)=["\']http://', content)
                    if http_resources:
                        score -= 10
                        AuditIssue.objects.create(
                            audit=audit, category="security", severity="warning",
                            title=f"{len(http_resources)} mixed content resources detected",
                            description="Your HTTPS page loads some resources over HTTP, which browsers may block.",
                            recommendation="Change all resource URLs to HTTPS, or use protocol-relative URLs (//).",
                            impact_score=10,
                        )

            # ── Server Information Exposure ──
            server_header = headers.get("Server", "")
            x_powered = headers.get("X-Powered-By", "")
            if server_header and any(v in server_header.lower() for v in ["apache/", "nginx/", "iis/"]):
                score -= 3
                AuditIssue.objects.create(
                    audit=audit, category="security", severity="info",
                    title=f"Server version exposed: {server_header}",
                    description="Exposing server version helps attackers target known vulnerabilities.",
                    recommendation="Remove or obfuscate the Server header in your web server config.",
                    impact_score=3,
                )
            if x_powered:
                score -= 3
                AuditIssue.objects.create(
                    audit=audit, category="security", severity="info",
                    title=f"X-Powered-By header exposed: {x_powered}",
                    description="This header reveals your technology stack to potential attackers.",
                    recommendation="Remove the X-Powered-By header from your server configuration.",
                    impact_score=3,
                )

        except requests.RequestException as e:
            logger.error(f"Security analysis failed for {url}: {e}")
            score = 0

        return {"score": max(0, min(100, score))}
