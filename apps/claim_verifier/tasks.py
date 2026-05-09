"""Celery tasks for the claim_verifier app."""
from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger("apps")


@shared_task(name="apps.claim_verifier.tasks.extract_claims_for_result")
def extract_claims_for_result(result_id: str) -> int:
    from apps.claim_verifier.services.claim_extractor import (
        extract_claims_for_result as _impl,
    )
    try:
        return len(_impl(result_id))
    except Exception as exc:  # pragma: no cover
        logger.exception("extract_claims_for_result(%s) failed: %s", result_id, exc)
        return 0


@shared_task(name="apps.claim_verifier.tasks.verify_claims_for_audit")
def verify_claims_for_audit(audit_id: str) -> int:
    from apps.claim_verifier.services.verifier import (
        verify_claims_for_audit as _impl,
    )
    try:
        return _impl(audit_id)
    except Exception as exc:  # pragma: no cover
        logger.exception("verify_claims_for_audit(%s) failed: %s", audit_id, exc)
        return 0
