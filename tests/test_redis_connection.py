#!/usr/bin/env python3
"""
Redis connection tests.

This module tests basic Redis connectivity and operations.
Run with: pytest tests/test_redis_connection.py -v
Or directly: python tests/test_redis_connection.py

Environment Variables:
    REDIS_URL: Redis connection URL (default: redis://192.168.4.246:6380/2)
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from redis.client import Redis


# =============================================================================
# Tests
# =============================================================================

@pytest.mark.redis
class TestRedisConnection:
    """Tests for Redis connection and basic operations."""

    def test_redis_ping(self, redis_client: Redis) -> None:
        """Test that Redis server responds to ping.

        Verifies basic connectivity to the Redis server.
        """
        result = redis_client.ping()
        assert result is True, "Redis ping should return True"

    def test_redis_write_read(self, redis_client: Redis) -> None:
        """Test basic write and read operations.

        Verifies that we can write a value to Redis and read it back.
        """
        test_key = "test:connection:write_read"
        test_value = "ok"

        # Write
        set_result = redis_client.set(test_key, test_value, ex=60)
        assert set_result is True, "Redis set should return True"

        # Read
        read_value = redis_client.get(test_key)
        assert read_value == test_value, f"Expected '{test_value}', got '{read_value}'"

    def test_redis_delete(self, redis_client: Redis) -> None:
        """Test delete operation.

        Verifies that we can delete keys from Redis.
        """
        test_key = "test:connection:delete"

        # Setup
        redis_client.set(test_key, "value", ex=60)

        # Delete
        delete_count = redis_client.delete(test_key)
        assert delete_count == 1, "Should delete exactly 1 key"

        # Verify deletion
        value = redis_client.get(test_key)
        assert value is None, "Key should not exist after deletion"

    def test_redis_expire(self, redis_client: Redis) -> None:
        """Test key expiration.

        Verifies that keys can be set with expiration times.
        """
        test_key = "test:connection:expire"

        # Set with 1 second expiration
        redis_client.set(test_key, "value", ex=1)

        # Should exist immediately
        assert redis_client.get(test_key) == "value"

        # TTL should be positive
        ttl = redis_client.ttl(test_key)
        assert ttl > 0, "TTL should be positive"

    def test_redis_list_operations(self, redis_client: Redis) -> None:
        """Test list operations.

        Verifies basic list push and range operations.
        """
        test_key = "test:connection:list"

        # Push items
        redis_client.rpush(test_key, "item1", "item2", "item3")

        # Get range
        items = redis_client.lrange(test_key, 0, -1)
        assert items == ["item1", "item2", "item3"]

        # Cleanup
        redis_client.delete(test_key)

    def test_redis_sorted_set_operations(self, redis_client: Redis) -> None:
        """Test sorted set operations.

        Verifies zadd and zrange operations used by keyword search.
        """
        test_key = "test:connection:zset"

        # Add items with scores
        redis_client.zadd(test_key, {"item1": 1.0, "item2": 2.0, "item3": 3.0})

        # Get range
        items = redis_client.zrange(test_key, 0, -1, withscores=False)
        assert items == ["item1", "item2", "item3"]

        # Cleanup
        redis_client.delete(test_key)


# =============================================================================
# Backward Compatibility
# =============================================================================

def test_redis_connection(redis_client: Redis) -> bool:
    """Legacy function for backward compatibility.

    This function can be called directly for simple connection testing.

    Args:
        redis_client: Redis client fixture

    Returns:
        True if connection is successful, False otherwise
    """
    try:
        pong = redis_client.ping()
        redis_client.set("test:connection", "ok", ex=60)
        value = redis_client.get("test:connection")
        redis_client.delete("test:connection")
        return pong and value == "ok"
    except Exception as e:
        print(f"[ERROR] Redis connection failed: {e}")
        return False


# =============================================================================
# Main Entry Point (Backward Compatibility)
# =============================================================================

if __name__ == "__main__":
    """Allow running tests directly with: python test_redis_connection.py"""
    # Run pytest with current file
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
