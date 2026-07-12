"""Narrative Watch agent.

Catches *emerging* narratives before they become full-blown reputation
problems. Two signals:

1. **Google Trends rising queries** for each brand term. A "Breakout" or
   +500% rising query attached to our brand is worth flagging even before
   we know what the story is -- the user can then investigate the query.
2. **Reddit new-post velocity** for brand mentions in the last day. When
   the count of new posts about the brand jumps above the agent's
   sensitivity threshold we raise an emerging-narrative alert.
"""
from __future__ import annotations

from apps.brand_vault.models import SafetyAlert

from ..base import BaseSecurityAgent, Finding
from ..judge import judge_finding
from ..sources import reddit, trends
from ._helpers import brand_terms

ALLOWED_ISSUES = (
    SafetyAlert.ISSUE_EMERGING_NARRATIVE,
    SafetyAlert.ISSUE_NEGATIVE,
)

# Minimum SerpAPI rising-value that qualifies as a "spike".
_SPIKE_MIN = 500


class NarrativeWatchAgent(BaseSecurityAgent):
    agent_id = "narrative_watch"
    display_name = "Narrative Watch"
    tagline = "Catches emerging narratives before they trend"
    color = "amber"
    sources = (SafetyAlert.SOURCE_TRENDS, SafetyAlert.SOURCE_REDDIT)

    def run(self, website, config):
        terms = brand_terms(website, config)
        if not terms:
            return []

        findings: list[Finding] = []
        spike_min = int(config.get("spike_min") or _SPIKE_MIN)
        for term in terms:
            for row in trends.rising_related(term):
                if row["value"] < spike_min:
                    continue
                findings.append(Finding(
                    source=SafetyAlert.SOURCE_TRENDS,
                    title=f"Rising query: {row['query']}",
                    snippet=(
                        f"Google Trends shows '{row['query']}' rising"
                        f" (+{row['value']}%) for brand term '{term}'."
                    ),
                    source_url=row.get("link") or "",
                    extra={
                        "brand_term": term,
                        "rising_query": row["query"],
                        "value": row["value"],
                    },
                ))

            for post in reddit.search_mentions(term, limit=15):
                findings.append(Finding(
                    source=SafetyAlert.SOURCE_REDDIT,
                    title=post["title"],
                    snippet=post.get("snippet") or "",
                    source_url=post.get("url") or "",
                    extra={
                        "brand_term": term,
                        "subreddit": post.get("subreddit"),
                        "score": post.get("score"),
                    },
                ))
        return findings

    def judge(self, website, finding):
        terms = brand_terms(website, {})
        brand = terms[0] if terms else website.name
        if finding.source == SafetyAlert.SOURCE_TRENDS:
            question = (
                "This is a rising Google search query attached to our brand."
                " Should we flag it as an emerging narrative worth"
                " investigating (spikes with negative modifiers are usually"
                " worth flagging even without content)?"
            )
        else:
            question = (
                "A Reddit post is mentioning our brand. Is this an emerging"
                " narrative worth flagging (negative, misleading, or gaining"
                " traction)?"
            )
        return judge_finding(
            question=question,
            brand=brand,
            title=finding.title,
            snippet=finding.snippet,
            allowed_issues=ALLOWED_ISSUES,
        )
