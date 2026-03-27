"""
Circuit breaker for Stripe API calls.

Prevents cascading failures when Stripe is down — returns cached/stale
subscription data from the DB instead of throwing 500s.

States:
    CLOSED   — normal operation, all calls go through
    OPEN     — Stripe failing, short-circuit all calls (use DB cache)
    HALF_OPEN — after cooldown, allow one test call through

Opens after `failure_threshold` failures within `window_seconds`.
Auto-transitions to HALF_OPEN after `recovery_timeout` seconds.
"""

import logging
import threading
import time
from enum import Enum
from functools import wraps

import stripe

logger = logging.getLogger("billing")


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Thread-safe circuit breaker for external API calls."""

    def __init__(
        self,
        name: str = "stripe",
        failure_threshold: int = 3,
        recovery_timeout: int = 30,
        window_seconds: int = 60,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.window_seconds = window_seconds

        self._state = CircuitState.CLOSED
        self._failures: list[float] = []
        self._last_failure_time: float = 0
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN:
                # Check if recovery timeout has elapsed → transition to HALF_OPEN
                if time.time() - self._last_failure_time >= self.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    logger.info(f"Circuit breaker [{self.name}] → HALF_OPEN (testing)")
            return self._state

    @property
    def is_available(self) -> bool:
        return self.state in (CircuitState.CLOSED, CircuitState.HALF_OPEN)

    def record_success(self):
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                logger.info(f"Circuit breaker [{self.name}] → CLOSED (recovered)")
            self._state = CircuitState.CLOSED
            self._failures.clear()

    def record_failure(self):
        now = time.time()
        with self._lock:
            # Prune old failures outside the window
            self._failures = [t for t in self._failures if now - t < self.window_seconds]
            self._failures.append(now)
            self._last_failure_time = now

            if self._state == CircuitState.HALF_OPEN:
                # Test call failed — reopen
                self._state = CircuitState.OPEN
                logger.warning(f"Circuit breaker [{self.name}] → OPEN (test call failed)")
            elif len(self._failures) >= self.failure_threshold:
                self._state = CircuitState.OPEN
                logger.warning(
                    f"Circuit breaker [{self.name}] → OPEN "
                    f"({len(self._failures)} failures in {self.window_seconds}s)"
                )

    def get_status(self) -> dict:
        """Return circuit breaker status for health checks."""
        return {
            "name": self.name,
            "state": self.state.value,
            "recent_failures": len(self._failures),
            "failure_threshold": self.failure_threshold,
            "recovery_timeout_seconds": self.recovery_timeout,
        }


# ── Module-level singleton ──
stripe_circuit = CircuitBreaker(name="stripe", failure_threshold=3, recovery_timeout=30)


# ── Transient errors that should trigger the circuit breaker ──
TRANSIENT_STRIPE_ERRORS = (
    stripe.error.APIConnectionError,
    stripe.error.RateLimitError,
)


def with_circuit_breaker(fallback=None):
    """
    Decorator that wraps a function with circuit breaker protection.

    If the circuit is open, calls `fallback(*args, **kwargs)` instead.
    If no fallback is provided, raises a GrowthPilotException.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not stripe_circuit.is_available:
                if fallback:
                    logger.info(f"Circuit open — using fallback for {func.__name__}")
                    return fallback(*args, **kwargs)
                from core.exceptions import GrowthPilotException
                raise GrowthPilotException(
                    "Billing service is temporarily unavailable. Your subscription is safe.",
                    code="billing_unavailable",
                    status_code=503,
                )

            try:
                result = func(*args, **kwargs)
                stripe_circuit.record_success()
                return result
            except TRANSIENT_STRIPE_ERRORS as e:
                stripe_circuit.record_failure()
                logger.error(f"Stripe transient error in {func.__name__}: {e}")
                if fallback:
                    return fallback(*args, **kwargs)
                raise
            except stripe.error.StripeError:
                # Non-transient errors (invalid request, auth, etc.) — don't trip the breaker
                raise

        return wrapper
    return decorator
