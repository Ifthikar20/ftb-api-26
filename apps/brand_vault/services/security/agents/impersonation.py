"""Impersonation agent.

Detects lookalike domains (typosquats, homograph variants) and lookalike
Reddit / X handles that could be impersonating the brand. First-pass
discovery is a SERP query for the brand across common phishing patterns.
The judge is then asked whether the returned domain / handle is a
plausible impersonation given the brand's real domain.

X and full WHOIS lookups are v2 follow-ups; the current implementation uses
SERP + Reddit + heuristic Levenshtein distance on domains.
"""
from __future__ import annotations

from urllib.parse import urlparse

from apps.brand_vault.models import SafetyAlert

from ..base import BaseSecurityAgent, Finding
from ..judge import judge_finding
from ..sources import reddit, serp
from ._helpers import brand_terms, website_domain


ALLOWED_ISSUES = (
    SafetyAlert.ISSUE_IMPERSONATION,
    SafetyAlert.ISSUE_HARMFUL,
)


class ImpersonationAgent(BaseSecurityAgent):
    agent_id = "impersonation"
    display_name = "Impersonation"
    tagline = "Finds typosquat domains and fake handles using your brand"
    color = "red"
    sources = (SafetyAlert.SOURCE_SERP, SafetyAlert.SOURCE_REDDIT)

    def run(self, website, config):
        terms = brand_terms(website, config)
        if not terms:
            return []
        own = website_domain(website)
        own_root = own.split(".")[0] if "." in own else own

        findings: list[Finding] = []
        for term in terms:
            queries = [
                f"{term} login",
                f"{term} support",
                f"{term} official",
                f'"{term}"',
            ]
            seen: set[str] = set()
            for query in queries:
                for result in serp.search(query, num=10):
                    domain = result["domain"]
                    if not domain or domain in seen:
                        continue
                    if own and own in domain:
                        continue
                    seen.add(domain)
                    if _looks_like_typosquat(domain, own_root, term):
                        findings.append(Finding(
                            source=SafetyAlert.SOURCE_SERP,
                            title=result["title"],
                            snippet=(
                                f"Domain '{domain}' appears in results for"
                                f" '{query}' and resembles our brand."
                            ),
                            source_url=result["url"],
                            extra={"domain": domain, "brand_query": query},
                        ))
            for post in reddit.search_mentions(term, limit=10):
                author_url = post.get("url") or ""
                if _reddit_handle_looks_like_brand(author_url, term):
                    findings.append(Finding(
                        source=SafetyAlert.SOURCE_REDDIT,
                        title=post["title"],
                        snippet=post.get("snippet") or "",
                        source_url=author_url,
                        extra={"brand_term": term},
                    ))
        return findings

    def judge(self, website, finding):
        terms = brand_terms(website, {})
        brand = terms[0] if terms else website.name
        own = website_domain(website)
        return judge_finding(
            question=(
                f"Our brand's real domain is '{own}'. Does this result look"
                " like an impersonation, phishing site, or fake handle"
                " abusing our brand name?"
            ),
            brand=brand,
            title=finding.title,
            snippet=finding.snippet,
            allowed_issues=ALLOWED_ISSUES,
        )


def _looks_like_typosquat(domain: str, own_root: str, term: str) -> bool:
    """Cheap heuristic: same brand name but a different root than ours."""
    if not domain or not own_root:
        return False
    domain_root = domain.split(".")[0]
    term_slug = term.lower().replace(" ", "")
    if term_slug and term_slug in domain_root.lower() and domain_root.lower() != own_root.lower():
        return True
    if _edit_distance(domain_root.lower(), own_root.lower()) == 1:
        return True
    return False


def _reddit_handle_looks_like_brand(url: str, term: str) -> bool:
    parsed = urlparse(url)
    if "reddit.com" not in parsed.netloc:
        return False
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2 or parts[0] != "user":
        return False
    handle = parts[1].lower()
    slug = term.lower().replace(" ", "")
    return bool(slug) and slug in handle


def _edit_distance(a: str, b: str) -> int:
    """Simple Levenshtein — used only on short domain roots so O(n*m) is fine."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        curr = [i]
        for j, cb in enumerate(b, start=1):
            curr.append(min(
                curr[-1] + 1,
                prev[j] + 1,
                prev[j - 1] + (0 if ca == cb else 1),
            ))
        prev = curr
    return prev[-1]
