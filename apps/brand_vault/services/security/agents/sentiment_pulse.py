"""Sentiment Pulse agent.

Reads Reddit and X mentions of the brand and flags any post whose judged
sentiment score falls below the sensitivity floor. Where the SERP and
Narrative Watch agents look at *what is being said*, Sentiment Pulse
focuses on *how* it is being said so the user sees mood shifts even when
the underlying story is small.
"""
from __future__ import annotations

from apps.brand_vault.models import SafetyAlert

from ..base import BaseSecurityAgent, Finding
from ..judge import judge_finding
from ..sources import reddit, x
from ._helpers import brand_terms


ALLOWED_ISSUES = (
    SafetyAlert.ISSUE_SENTIMENT_DROP,
    SafetyAlert.ISSUE_NEGATIVE,
    SafetyAlert.ISSUE_HARMFUL,
)


class SentimentPulseAgent(BaseSecurityAgent):
    agent_id = "sentiment_pulse"
    display_name = "Sentiment Pulse"
    tagline = "Tracks sentiment shifts and harmful mentions across social"
    color = "teal"
    sources = (SafetyAlert.SOURCE_REDDIT, SafetyAlert.SOURCE_X)

    def run(self, website, config):
        terms = brand_terms(website, config)
        if not terms:
            return []
        findings: list[Finding] = []
        for term in terms:
            for post in reddit.search_mentions(term, limit=25):
                findings.append(Finding(
                    source=SafetyAlert.SOURCE_REDDIT,
                    title=post["title"],
                    snippet=post.get("snippet") or "",
                    source_url=post.get("url") or "",
                    extra={"brand_term": term, "subreddit": post.get("subreddit")},
                ))
            for tweet in x.search_mentions(term, limit=25):
                findings.append(Finding(
                    source=SafetyAlert.SOURCE_X,
                    title=tweet["title"],
                    snippet=tweet.get("snippet") or "",
                    source_url=tweet.get("url") or "",
                    extra={"brand_term": term, "author_id": tweet.get("author_id")},
                ))
        return findings

    def judge(self, website, finding):
        terms = brand_terms(website, {})
        brand = terms[0] if terms else website.name
        return judge_finding(
            question=(
                "Score the sentiment of this mention toward the brand."
                " Flag it if the tone is negative, hostile or harmful."
            ),
            brand=brand,
            title=finding.title,
            snippet=finding.snippet,
            allowed_issues=ALLOWED_ISSUES,
        )
