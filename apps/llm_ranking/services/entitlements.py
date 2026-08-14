"""
The single place that decides whether a user may spend money on an audit.

There are two code paths that create an ``LLMRankingAudit`` and dispatch it:

  1. ``LLMRankingAuditListView.post``      — the Run Audit modal
  2. ``WebsitePromptCreateView._trigger_scan`` — the auto-scan fired when a
     prompt is created on the Prompts page

Only the first ever checked anything, so creating prompts was an unmetered way
to run audits: no spend cap, every configured provider regardless of plan, and
no prompt cap. Because the create handler splits input per line and supports
bulk upload, a single paste could queue hundreds of prompts against every
provider on a plan entitled to five prompts and two providers.

Copying the checks into the second path would leave two things to drift. This
module is the one implementation both call.

Note that ``limits_for_user`` short-circuits to the Enterprise limits whenever
``PAYWALL_ENABLED`` is false, which is the default. Every gate here is
therefore inert until the paywall is switched on — which is what makes turning
them on low-risk, not what makes them pointless.
"""
from __future__ import annotations

import logging

from django.conf import settings

from core.utils.constants import max_prompts_for_user, providers_allowed_for_user

logger = logging.getLogger(__name__)


class AuditNotAllowed(Exception):
    """A plan limit or the spend cap blocks this audit.

    Carries the response shape the API already returns for a blocked run, so
    callers translate rather than invent. ``payload`` matches the envelope the
    Run Audit modal already parses.
    """

    def __init__(self, code: str, detail: str, *, http_status: int = 402,
                 extra: dict | None = None):
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.http_status = http_status
        self.extra = extra or {}

    @property
    def payload(self) -> dict:
        return {"error": self.code, "detail": self.detail, **self.extra}


def assert_within_spend_cap(user) -> None:
    """Raise :class:`AuditNotAllowed` if the user is at their monthly AI cap.

    ``monthly_ai_cost_cap_usd`` of 0 means no cap. Spend covers every module
    that writes to ``AITokenUsage``, not just LLM ranking.
    """
    cap = float(getattr(user, "monthly_ai_cost_cap_usd", 0) or 0)
    if cap <= 0:
        return

    from core.ai_tracking import month_to_date_cost

    spent = month_to_date_cost(user)
    if spent >= cap:
        raise AuditNotAllowed(
            "monthly_ai_cost_cap_exceeded",
            (
                f"Month-to-date AI spend ${spent:.2f} has reached your cap of "
                f"${cap:.2f}. Raise the cap in Settings or wait until the next "
                f"billing month."
            ),
            extra={"cap_status": {"spent_usd": round(spent, 4), "cap_usd": cap}},
        )


def resolve_providers(user, requested: list[str] | None) -> list[str]:
    """Return the provider keys this audit may actually query.

    Three filters, in order: the provider must be implemented (in
    ``PROVIDERS`` — stubs in ``PROVIDER_CHOICES`` are excluded so the UI can
    never queue a run that silently produces no results), have an API key
    configured, and be permitted by the user's plan.

    Falls back to ``["claude"]`` when the intersection is empty, matching the
    behaviour the audit runner already relied on — an audit with no providers
    would produce nothing at all.
    """
    from apps.llm_ranking.providers import PROVIDERS

    keys = list(requested) if requested else list(PROVIDERS.keys())
    allowed = providers_allowed_for_user(user)

    resolved = []
    for key in keys:
        cls = PROVIDERS.get(key)
        if cls is None:
            continue
        if not getattr(settings, cls.api_key_setting, ""):
            continue
        if allowed and key not in allowed:
            continue
        resolved.append(key)

    if resolved:
        return resolved

    # Nothing survived. If the plan permits claude, use it; otherwise use the
    # first permitted+configured provider so the run still does something.
    if not allowed or "claude" in allowed:
        return ["claude"]
    for key in allowed:
        cls = PROVIDERS.get(key)
        if cls is not None and getattr(settings, cls.api_key_setting, ""):
            return [key]
    return ["claude"]


def cap_prompts(user, prompts: list) -> list:
    """Truncate ``prompts`` to the user's per-audit plan cap.

    ``generate_prompts`` already applies this on the auto-generated path, but
    custom prompts arrive straight from the serializer — which caps the list at
    10 with no reference to the plan — and the auto-scan path applied no cap at
    all. Truncating here covers every path.
    """
    cap = max_prompts_for_user(user)
    if cap > 0 and len(prompts) > cap:
        logger.info(
            "Truncating audit prompts from %d to plan cap %d for user %s",
            len(prompts), cap, getattr(user, "id", None),
        )
        return prompts[:cap]
    return prompts
