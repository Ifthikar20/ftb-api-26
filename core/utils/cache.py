import functools
from collections.abc import Callable
from typing import Any

from django.core.cache import cache


def cache_result(key: str, timeout: int = 300):
    """Decorator to cache a function's return value in Redis."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cached = cache.get(key)
            if cached is not None:
                return cached
            result = func(*args, **kwargs)
            cache.set(key, result, timeout)
            return result
        return wrapper
    return decorator


def invalidate_cache(key: str) -> None:
    cache.delete(key)


def get_or_set(key: str, callable_fn: Callable, timeout: int = 300) -> Any:
    return cache.get_or_set(key, callable_fn, timeout)


def make_cache_key(*parts) -> str:
    """Build a consistent cache key from parts."""
    return ":".join(str(p) for p in parts)
