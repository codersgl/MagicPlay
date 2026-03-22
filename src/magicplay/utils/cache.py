"""
Cache utilities for resource management.

Provides simple caching mechanisms for generated resources.
"""

import hashlib
import json
from datetime import datetime, timedelta
from functools import lru_cache, wraps
from pathlib import Path
from typing import Any, Callable, Dict, Optional, TypeVar, Union

from loguru import logger

from magicplay.config import Settings

T = TypeVar("T")


class SimpleCache:
    """
    Simple in-memory cache with TTL support.

    For persistent caching, use ResourceRegistry instead.
    """

    def __init__(self, max_size: int = 1000, default_ttl_hours: int = 24):
        """
        Initialize cache.

        Args:
            max_size: Maximum number of items in cache
            default_ttl_hours: Default time-to-live in hours
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._max_size = max_size
        self._default_ttl = timedelta(hours=default_ttl_hours)

    def _generate_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        key_data = {
            "args": args,
            "kwargs": kwargs,
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.sha256(key_str.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        if key not in self._cache:
            return None

        entry = self._cache[key]
        expires_at = entry.get("expires_at")

        if expires_at and datetime.now() > expires_at:
            # Entry expired
            del self._cache[key]
            return None

        return entry.get("value")

    def set(self, key: str, value: Any, ttl: Optional[timedelta] = None) -> None:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live (uses default if not specified)
        """
        # Evict oldest if at capacity
        if len(self._cache) >= self._max_size:
            self._evict_oldest()

        self._cache[key] = {
            "value": value,
            "created_at": datetime.now(),
            "expires_at": datetime.now() + (ttl or self._default_ttl),
        }

    def delete(self, key: str) -> bool:
        """Delete item from cache."""
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> None:
        """Clear all items from cache."""
        self._cache.clear()

    def _evict_oldest(self) -> None:
        """Evict oldest entry."""
        if not self._cache:
            return

        oldest_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].get("created_at", datetime.now()),
        )
        del self._cache[oldest_key]

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries.

        Returns:
            Number of entries removed
        """
        now = datetime.now()
        expired_keys = [
            k
            for k, v in self._cache.items()
            if v.get("expires_at") and now > v["expires_at"]
        ]

        for key in expired_keys:
            del self._cache[key]

        return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        now = datetime.now()
        expired_count = sum(
            1
            for v in self._cache.values()
            if v.get("expires_at") and now > v["expires_at"]
        )

        return {
            "total_items": len(self._cache),
            "max_size": self._max_size,
            "expired_items": expired_count,
            "utilization": (
                len(self._cache) / self._max_size if self._max_size > 0 else 0
            ),
        }


def cached(
    cache: Optional[SimpleCache] = None,
    ttl: Optional[timedelta] = None,
    key_prefix: str = "",
) -> Callable:
    """
    Decorator for caching function results.

    Args:
        cache: Cache instance (creates new one if None)
        ttl: Time-to-live for cached entries
        key_prefix: Prefix for cache keys

    Returns:
        Decorated function with caching

    Usage:
        @cached(ttl=timedelta(hours=1))
        def expensive_operation(x, y):
            ...
    """
    local_cache = cache or SimpleCache()

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            key_data = {
                "function": f"{func.__module__}.{func.__name__}",
                "args": args,
                "kwargs": kwargs,
            }
            key_str = json.dumps(key_data, sort_keys=True, default=str)
            cache_key = f"{key_prefix}{hashlib.sha256(key_str.encode()).hexdigest()}"

            # Try cache first
            cached_result = local_cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_result

            # Call function
            result = func(*args, **kwargs)

            # Cache result
            local_cache.set(cache_key, result, ttl=ttl)
            logger.debug(f"Cache miss for {func.__name__}, result cached")

            return result

        return wrapper

    return decorator


def memoize(func: Callable) -> Callable:
    """
    Simple memoization decorator using lru_cache.

    Args:
        func: Function to memoize

    Returns:
        Memoized function
    """
    return lru_cache(maxsize=128)(func)
