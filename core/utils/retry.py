import functools
import logging
import time
from collections.abc import Callable

logger = logging.getLogger("apps")


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    exponential_base: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
):
    """
    Decorator for exponential backoff retry logic.
    Useful for external API calls (Stripe, OpenAI, DataForSEO).
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt < max_retries - 1:
                        delay = base_delay * (exponential_base ** attempt)
                        logger.warning(
                            f"Retry {attempt + 1}/{max_retries} for {func.__name__}: {exc}. "
                            f"Waiting {delay}s."
                        )
                        time.sleep(delay)
            raise last_exc
        return wrapper
    return decorator
