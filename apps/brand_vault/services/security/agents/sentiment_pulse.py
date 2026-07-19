"""Sentiment Pulse agent.

Reads Reddit and X mentions of the brand and flags any post whose judged
sentiment score falls below the sensitivity floor. Where the SERP and
Narrative Watch agents look at *what is being said*, Sentiment Pulse
focuses on *how* it is being said so the user sees mood shifts even when
the underlying story is small.

Search coverage comes from two places: the Monitoring config's brand
terms (or user-defined SafetyPrompts), plus distinctive phrases derived
from the client's Brand Input knowledge base — product names and titles
people may use on social without naming the brand itself.

Judging is grounded: each post is checked against the most relevant
chunks of the client's own brand material, so a post spreading a factual
falsehood in a neutral tone is still catchable, and every alert carries
the evidence trail the UI shows as "Verified against N brand sources".
"""
from __future__ import annotations

from apps.brand_vault.models import SafetyAlert, SafetyPrompt
from apps.rag.services.retriever import retrieve

from ..base import BaseSecurityAgent, Finding
from ..derived_terms import derived_search_terms
from ..judge import judge_finding
from ..sources import reddit, x
from ._helpers import brand_terms

ALLOWED_ISSUES = (
    SafetyAlert.ISSUE_SENTIMENT_DROP,
    SafetyAlert.ISSUE_NEGATIVE,
    SafetyAlert.ISSUE_HARMFUL,
)

# Ground each social mention in up to this many knowledge-base chunks
# when judging. Keeps the judge prompt bounded.
_GROUND_TRUTH_TOP_K = 5


class SentimentPulseAgent(BaseSecurityAgent):
    agent_id = "sentiment_pulse"
    display_name = "Sentiment Pulse"
    tagline = "Tracks sentiment shifts and harmful mentions across social"
    color = "teal"
    sources = (SafetyAlert.SOURCE_REDDIT, SafetyAlert.SOURCE_X)

    def run(self, website, config):
        user_prompts = list(
            SafetyPrompt.objects.filter(
                website=website,
                agent_id=self.agent_id,
                status=SafetyPrompt.STATUS_ACTIVE,
            ).values_list("text", flat=True),
        )
        queries = list(user_prompts or brand_terms(website, config))
        if not queries:
            return []

        # Widen the search with phrases mined from the client's ingested
        # brand material (product names, doc titles). Marked in extra so
        # the alert shows which query surfaced the post.
        derived = derived_search_terms(website, exclude=queries)
        seen_urls: set[str] = set()

        findings: list[Finding] = []
        for query in queries + derived:
            is_derived = query in derived
            for post in reddit.search_mentions(query, limit=25):
                url = post.get("url") or ""
                if url and url in seen_urls:
                    continue
                if url:
                    seen_urls.add(url)
                findings.append(Finding(
                    source=SafetyAlert.SOURCE_REDDIT,
                    title=post["title"],
                    snippet=post.get("snippet") or "",
                    source_url=url,
                    extra={
                        "brand_term": query,
                        "subreddit": post.get("subreddit"),
                        "derived_term": is_derived,
                    },
                ))
            for tweet in x.search_mentions(query, limit=25):
                url = tweet.get("url") or ""
                if url and url in seen_urls:
                    continue
                if url:
                    seen_urls.add(url)
                findings.append(Finding(
                    source=SafetyAlert.SOURCE_X,
                    title=tweet["title"],
                    snippet=tweet.get("snippet") or "",
                    source_url=url,
                    extra={
                        "brand_term": query,
                        "author_id": tweet.get("author_id"),
                        "derived_term": is_derived,
                    },
                ))
        return findings

    def judge(self, website, finding):
        terms = brand_terms(website, {})
        brand = terms[0] if terms else website.name

        # Pull the client's own statements relevant to this post so the
        # judge can also catch calm-toned factual falsehoods, not just
        # hostile tone. Same pattern as the LLM Truth agent.
        hits: list = []
        query = f"{finding.title} {finding.snippet}".strip()[:500] or brand
        try:
            hits = retrieve(
                user=website.user,
                website=website,
                query=query,
                top_k=_GROUND_TRUTH_TOP_K,
            )
        except Exception:
            # Retrieval must never break the agent — fall back to
            # ungrounded judging if the RAG layer errors out.
            hits = []

        ground_truth = [
            {
                "chunk_id": h.chunk_id,
                "source_id": h.source_id,
                "source_url": h.source_url,
                "section_label": h.section_label,
                "text": h.text,
                "score": h.score,
            }
            for h in hits
        ]
        # Stash on the finding so ``scan()`` persists it on the alert.
        finding.extra["evidence_chunks"] = ground_truth

        return judge_finding(
            question=(
                "Score the sentiment of this mention toward the brand."
                " Flag it if the tone is negative, hostile or harmful,"
                " or if it contradicts the brand's own stated facts."
            ),
            brand=brand,
            title=finding.title,
            snippet=finding.snippet,
            allowed_issues=ALLOWED_ISSUES,
            ground_truth=ground_truth,
        )
