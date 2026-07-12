"""SERP Reputation agent.

Watches Google search results for the brand. Two failure modes worth
alerting on:

1. **negative_outranking** — for a plain brand query, an external page
   with negative framing ranks above our own domain.
2. **ranking_for_bad_query** — we rank in the top 10 for a brand + negative
   keyword combo (e.g. "acme scam"). Even if the ranking page is our own
   response page, this is a signal the user wants to see.
"""
from __future__ import annotations

from apps.brand_vault.models import SafetyAlert, SafetyPrompt

from ..base import BaseSecurityAgent, Finding
from ..judge import judge_finding
from ..sources import serp
from ._helpers import brand_terms, negative_keywords, website_domain

ALLOWED_ISSUES = (
    SafetyAlert.ISSUE_NEGATIVE_OUTRANKING,
    SafetyAlert.ISSUE_RANKING_FOR_BAD_QUERY,
    SafetyAlert.ISSUE_NEGATIVE,
    SafetyAlert.ISSUE_HARMFUL,
)


class SerpReputationAgent(BaseSecurityAgent):
    agent_id = "serp_reputation"
    display_name = "SERP Reputation"
    tagline = "Detects negative pages outranking you and bad queries you rank for"
    color = "blue"
    sources = (SafetyAlert.SOURCE_SERP,)

    def run(self, website, config):
        own = website_domain(website)

        user_prompts = list(
            SafetyPrompt.objects.filter(
                website=website,
                agent_id=self.agent_id,
                status=SafetyPrompt.STATUS_ACTIVE,
            ).values_list("text", flat=True),
        )
        if user_prompts:
            findings: list[Finding] = []
            for query in user_prompts:
                for result in serp.search(query, num=10):
                    findings.append(Finding(
                        source=SafetyAlert.SOURCE_SERP,
                        title=result["title"],
                        snippet=result.get("snippet") or "",
                        source_url=result["url"],
                        extra={
                            "brand_query": query,
                            "serp_rank": result.get("serp_rank"),
                            "domain": result["domain"],
                            "mode": "user_prompt",
                            "own_page": bool(own and own in result["domain"]),
                        },
                    ))
            return findings

        terms = brand_terms(website, config)
        if not terms:
            return []
        neg_words = negative_keywords(website, config)

        findings: list[Finding] = []
        for term in terms:
            for result in serp.search(term, num=10):
                if own and own in result["domain"]:
                    continue
                findings.append(Finding(
                    source=SafetyAlert.SOURCE_SERP,
                    title=result["title"],
                    snippet=result.get("snippet") or "",
                    source_url=result["url"],
                    extra={
                        "brand_query": term,
                        "serp_rank": result.get("serp_rank"),
                        "domain": result["domain"],
                        "mode": "brand_query",
                    },
                ))
            for word in neg_words:
                query = f"{term} {word}"
                for result in serp.search(query, num=10):
                    findings.append(Finding(
                        source=SafetyAlert.SOURCE_SERP,
                        title=result["title"],
                        snippet=result.get("snippet") or "",
                        source_url=result["url"],
                        extra={
                            "brand_query": query,
                            "serp_rank": result.get("serp_rank"),
                            "domain": result["domain"],
                            "mode": "negative_query",
                            "own_page": bool(own and own in result["domain"]),
                        },
                    ))
        return findings

    def judge(self, website, finding):
        terms = brand_terms(website, {})
        brand = terms[0] if terms else website.name
        mode = finding.extra.get("mode")
        query = finding.extra.get("brand_query") or ""
        rank = finding.extra.get("serp_rank")
        if mode == "brand_query":
            question = (
                f"Someone searched for '{query}' (our brand). Google returned"
                f" this page at rank {rank}. Is it negative, misleading or"
                " harmful toward our brand?"
            )
        elif mode == "user_prompt":
            question = (
                f"We are monitoring the query '{query}' for our brand-safety"
                f" bank. Google returned this page at rank {rank}. Does its"
                " content represent a brand-safety issue for our brand"
                " (e.g. our product mentioned negatively, complaints, or a"
                " competitor page dominating a query where we should appear)?"
            )
        else:
            question = (
                f"Someone searched for '{query}' and this page appeared at"
                f" rank {rank}. Does its content represent a brand-safety"
                " issue (e.g. accusations, complaints, misinformation)?"
            )
        return judge_finding(
            question=question,
            brand=brand,
            title=finding.title,
            snippet=finding.snippet,
            allowed_issues=ALLOWED_ISSUES,
        )
