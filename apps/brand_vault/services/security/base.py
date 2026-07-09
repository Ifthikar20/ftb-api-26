"""Base contract for Brand Security agents.

An agent turns raw signal from one or more sources into ``Alert``-shaped
verdicts. The framework is deliberately thin:

* ``Finding`` is a candidate captured by an agent's ``run()``. It carries the
  minimum context the ``judge()`` step needs to decide whether the finding is
  a real brand-safety issue.
* ``Verdict`` is the judge's output: issue class, severity, sentiment and a
  short reason. A ``Verdict`` with ``issue == "none"`` means the finding was
  harmless and gets dropped.
* ``BaseSecurityAgent`` wires the two together: subclasses implement ``run()``
  and ``judge()``; the orchestrator calls ``scan()`` which handles persistence
  and stamps every raised alert with the agent's id.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from apps.brand_vault.models import BrandSecurityAgent, SafetyAlert


@dataclass
class Finding:
    """One candidate observation an agent produced from a source."""

    source: str  # one of SafetyAlert.SOURCE_* constants
    title: str
    snippet: str
    source_url: str = ""
    model: str = ""  # populated by LLM Truth for provider attribution
    prompt_text: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class Verdict:
    """Judge output for a finding. ``issue == "none"`` drops the finding."""

    issue: str = "none"
    severity: str = "none"  # high | medium | low | none
    sentiment_score: float | None = None
    detail: str = ""


class BaseSecurityAgent:
    """Subclass contract: set ``agent_id``, override ``run`` and ``judge``.

    ``run`` returns findings (calls source clients, does not touch the DB).
    ``judge`` decides whether a finding is a real issue and how severe.
    The orchestrator invokes ``scan(website, config)`` and persists results.
    """

    #: Stable machine id used in the DB and API.
    agent_id: str = ""
    #: Human-readable label for the UI.
    display_name: str = ""
    #: Short one-liner explaining the agent's job.
    tagline: str = ""
    #: Colour hint the UI uses for the agent badge.
    color: str = "slate"
    #: Sources this agent draws signal from — informational, for the UI.
    sources: tuple[str, ...] = ()

    # ── Overrides ────────────────────────────────────────────────────────

    def run(
        self,
        website,
        config: dict[str, Any],
    ) -> list[Finding]:
        """Return raw findings this agent surfaced this run."""
        raise NotImplementedError

    def judge(self, website, finding: Finding) -> Verdict:
        """Adjudicate one finding. Default is a no-op verdict."""
        return Verdict()

    # ── Orchestrator hook — do not override without reason ───────────────

    def scan(
        self,
        website,
        agent_row: BrandSecurityAgent,
    ) -> list[SafetyAlert]:
        """Run + judge + persist. Returns the alerts that were created."""
        config = dict(agent_row.config or {})
        minimum = _sensitivity_min_severity(agent_row.sensitivity)
        alerts: list[SafetyAlert] = []
        for finding in self.run(website, config):
            verdict = self.judge(website, finding)
            if verdict.issue in ("", "none"):
                continue
            if verdict.severity in ("", "none"):
                continue
            if not _severity_passes(verdict.severity, minimum):
                continue
            if self._is_duplicate(website, finding, verdict):
                continue
            alert = SafetyAlert.objects.create(
                website=website,
                agent_id=self.agent_id,
                source=finding.source,
                source_url=finding.source_url[:1000],
                title=finding.title[:300],
                model=finding.model[:40],
                prompt_text=finding.prompt_text[:500],
                snippet=finding.snippet,
                issue=verdict.issue,
                detail=verdict.detail,
                severity=verdict.severity,
                sentiment_score=verdict.sentiment_score,
            )
            alerts.append(alert)
        return alerts

    def _is_duplicate(
        self,
        website,
        finding: Finding,
        verdict: Verdict,
    ) -> bool:
        """Dedupe on (agent, source_url) for open alerts of the same issue.

        Keeps the alerts table clean when a scan re-runs before the user
        has resolved anything. If ``source_url`` is empty (e.g. an LLM
        finding attributed to a prompt), we fall back to (title, issue).
        """
        qs = SafetyAlert.objects.filter(
            website=website,
            agent_id=self.agent_id,
            issue=verdict.issue,
            status=SafetyAlert.STATUS_OPEN,
        )
        if finding.source_url:
            return qs.filter(source_url=finding.source_url[:1000]).exists()
        return qs.filter(title=finding.title[:300]).exists()


_SEVERITY_ORDER = {"none": 0, "low": 1, "medium": 2, "high": 3}


def _sensitivity_min_severity(sensitivity: str) -> str:
    return {
        "low": "high",
        "medium": "medium",
        "high": "low",
    }.get(sensitivity, "medium")


def _severity_passes(severity: str, minimum: str) -> bool:
    return _SEVERITY_ORDER.get(severity, 0) >= _SEVERITY_ORDER.get(minimum, 2)
