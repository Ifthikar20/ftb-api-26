"""How a freshly-created scan audit gets executed.

Two modes, chosen by the ``LLM_SCAN_MODE`` setting:

* ``"celery"`` (default, production) — enqueue the chord-based
  ``run_llm_ranking_audit`` task on the broker.
* ``"inline"`` (default in dev) — run the audit in a background daemon
  thread via :meth:`LLMRankingService.run_audit_sync`, so a plain dev
  server with no Redis/worker still scans new prompts.
"""
from __future__ import annotations

import logging
import threading

from django.conf import settings
from django.db import connections

logger = logging.getLogger("apps")


def dispatch_scan(audit_id: str) -> str:
    """Run the audit via Celery or inline depending on ``LLM_SCAN_MODE``.

    Returns the dispatch mode actually used. Raises only if the Celery
    broker is required but unreachable, so callers can treat scanning as
    best-effort.
    """
    mode = getattr(settings, "LLM_SCAN_MODE", "celery")
    if mode == "inline":
        _run_inline(audit_id)
        return "inline"

    from apps.llm_ranking.tasks import run_llm_ranking_audit
    run_llm_ranking_audit.delay(audit_id=audit_id)
    return "queued"


def _run_inline(audit_id: str) -> None:
    def _run() -> None:
        from apps.llm_ranking.services.ranking_service import LLMRankingService
        try:
            LLMRankingService.run_audit_sync(audit_id=audit_id)
        except Exception:  # pragma: no cover - defensive
            logger.exception("inline scan failed for %s", audit_id)
        finally:
            # The thread has its own DB connections; close them so they
            # don't leak past the run.
            connections.close_all()

    threading.Thread(target=_run, name=f"scan-{audit_id}", daemon=True).start()
