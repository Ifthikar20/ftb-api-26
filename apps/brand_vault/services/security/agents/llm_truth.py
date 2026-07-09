"""LLM Truth agent.

Runs each active ``SafetyPrompt`` for the website against every configured
LLM provider (Claude, GPT, Gemini, Perplexity, Grok) and asks the judge
whether the answer contains a hallucination, outdated info, or an unverified
claim about the brand. Alerts get stamped with the model that gave the bad
answer so the user knows *which* LLM is misbehaving.
"""
from __future__ import annotations

from apps.brand_vault.models import SafetyAlert, SafetyPrompt

from ..base import BaseSecurityAgent, Finding
from ..judge import judge_finding
from ..sources import llms
from ._helpers import brand_terms


ALLOWED_ISSUES = (
    SafetyAlert.ISSUE_HALLUCINATION,
    SafetyAlert.ISSUE_UNVERIFIED,
    SafetyAlert.ISSUE_OUTDATED,
    SafetyAlert.ISSUE_HARMFUL,
    SafetyAlert.ISSUE_NEGATIVE,
)


class LLMTruthAgent(BaseSecurityAgent):
    agent_id = "llm_truth"
    display_name = "LLM Truth"
    tagline = "Catches wrong, outdated or harmful things LLMs say about you"
    color = "purple"
    sources = (SafetyAlert.SOURCE_LLM,)

    def run(self, website, config):
        prompts = list(
            SafetyPrompt.objects.filter(
                website=website, status=SafetyPrompt.STATUS_ACTIVE,
            ).values_list("text", flat=True),
        )
        if not prompts:
            # If the user hasn't configured any prompts, seed with a couple
            # of defaults using the brand name so the agent has something to
            # scan on its first run.
            terms = brand_terms(website, config)
            if not terms:
                return []
            brand = terms[0]
            prompts = [
                f"What is {brand}?",
                f"Tell me about {brand}",
                f"Is {brand} a scam?",
            ]

        findings: list[Finding] = []
        for prompt in prompts:
            answers = llms.ask_all_providers(prompt)
            for row in answers:
                findings.append(Finding(
                    source=SafetyAlert.SOURCE_LLM,
                    title=prompt[:200],
                    snippet=row["text"][:2000],
                    model=row["model"],
                    prompt_text=prompt,
                    extra={"provider": row["provider"]},
                ))
        return findings

    def judge(self, website, finding):
        terms = brand_terms(website, {})
        brand = terms[0] if terms else website.name
        return judge_finding(
            question=(
                "Does this LLM answer contain a factual error, outdated info,"
                " or unverified/harmful claim about the brand?"
            ),
            brand=brand,
            title=finding.prompt_text or finding.title,
            snippet=finding.snippet,
            allowed_issues=ALLOWED_ISSUES,
        )
