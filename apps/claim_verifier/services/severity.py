"""Severity bucketing helper.

The verifier reduces an aggregate score to a discrete severity label so
the dashboard can colour-code mismatches consistently. Pure function so
both the unit tests and the dashboard rollups can re-bucket without a
database round-trip.
"""
from __future__ import annotations

from apps.claim_verifier.models import MismatchSeverity


def bucket(score: float) -> str:
    """Map ``score`` (0-1) onto a :class:`MismatchSeverity` value."""
    s = float(score or 0.0)
    if s > 0.7:
        return MismatchSeverity.CRITICAL.value
    if s > 0.5:
        return MismatchSeverity.HIGH.value
    if s > 0.3:
        return MismatchSeverity.MEDIUM.value
    if s > 0.1:
        return MismatchSeverity.LOW.value
    return MismatchSeverity.INFO.value
