"""
Tests for cache utilities.
"""

from datetime import timedelta

import pytest

from magicplay.utils.cache import SimpleCache, cached, memoize


class TestSimpleCache:
    """Test SimpleCache functionality."""

    @pytest.fixture
    def cache(self):
        """Create a cache instance for tests."""
        return SimpleCache(max_size=3, default_ttl_hours=1)

    def test_cache_initialization(self, cache):
        """Test cache initialization with custom parameters."""
        assert cache._max_size == 3
        assert cache._default_ttl == timedelta(hours=1)
        assert len(cache._cache) == 0

    def test_cache_set_and_get(self, cache):
        """Test setting and getting values."""
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_cache_get_nonexistent(self, cache):
        """Test getting a non-existent key returns None."""
        assert cache.get("nonexistent") is None

    def test_cache_delete(self, cache):
        """Test deleting a key."""
        cache.set("key1", "value1")
        assert cache.delete("key1") is True
        assert cache.get("key1") is None

    def test_cache_delete_nonexistent(self, cache):
        """Test deleting a non-existent key returns False."""
        assert cache.delete("nonexistent") is False

    def test_cache_clear(self, cache):
        """Test clearing all cache entries."""
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        assert len(cache._cache) == 0

    def test_cache_eviction_when_full(self, cache):
        """Test that oldest entry is evicted when cache is full."""
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        cache.set("key4", "value4")  # Should evict key1 (oldest)

        assert cache.get("key1") is None  # Evicted
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"

    def test_cache_expiry(self, cache):
        """Test that expired entries are not returned."""
        cache.set("key1", "value1", ttl=timedelta(seconds=-1))  # Already expired
        assert cache.get("key1") is None

    def test_cleanup_expired(self, cache):
        """Test cleanup of expired entries."""
        cache.set("key1", "value1", ttl=timedelta(seconds=-1))  # Expired
        cache.set("key2", "value2")  # Not expired

        removed = cache.cleanup_expired()
        assert removed == 1
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"

    def test_get_stats(self, cache):
        """Test cache statistics."""
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        stats = cache.get_stats()
        assert stats["total_items"] == 2
        assert stats["max_size"] == 3
        assert stats["expired_items"] == 0
        assert 0 <= stats["utilization"] <= 1

    def test_generate_key(self, cache):
        """Test cache key generation from arguments."""
        key1 = cache._generate_key("arg1", "arg2", kwarg1="value1")
        key2 = cache._generate_key("arg1", "arg2", kwarg1="value1")
        key3 = cache._generate_key("arg1", "arg3", kwarg1="value1")

        # Same arguments should produce same key
        assert key1 == key2
        # Different arguments should produce different keys
        assert key1 != key3


class TestCachedDecorator:
    """Test the @cached decorator."""

    def test_cached_decorator_basic(self):
        """Test basic caching functionality with decorator."""
        cache = SimpleCache()

        call_count = 0

        @cached(cache=cache, ttl=timedelta(hours=1))
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call - should execute function
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count == 1

        # Second call with same args - should use cache
        result2 = expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # Not incremented

        # Call with different args - should execute function again
        result3 = expensive_function(10)
        assert result3 == 20
        assert call_count == 2

    def test_cached_decorator_with_key_prefix(self):
        """Test caching with key prefix."""
        cache = SimpleCache()

        @cached(cache=cache, key_prefix="prefix_")
        def func(x):
            return x

        func(1)
        # Key should have prefix
        stats = cache.get_stats()
        assert stats["total_items"] == 1


class TestMemoizeDecorator:
    """Test the @memoize decorator."""

    def test_memoize_basic(self):
        """Test basic memoization."""
        call_count = 0

        @memoize
        def expensive_operation(n):
            nonlocal call_count
            call_count += 1
            return n * n

        assert expensive_operation(5) == 25
        assert expensive_operation(5) == 25  # Cached
        assert expensive_operation(10) == 100
        assert call_count == 2

    def test_memoize_with_args(self):
        """Test memoization with multiple arguments."""
        call_count = 0

        @memoize
        def add(a, b):
            nonlocal call_count
            call_count += 1
            return a + b

        assert add(1, 2) == 3
        assert add(1, 2) == 3  # Cached
        assert add(2, 1) == 3  # Different args, not cached
        assert call_count == 2
