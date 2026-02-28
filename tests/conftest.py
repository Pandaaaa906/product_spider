"""
Pytest configuration and shared fixtures for product_spider tests.

This module provides common fixtures and configuration for all tests,
including Redis client setup, environment variable handling, and
shared test utilities.
"""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Generator

import pytest
import redis

# Add project root to Python path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

if TYPE_CHECKING:
    from redis.client import Redis


# =============================================================================
# Environment Configuration
# =============================================================================

def get_env_var(key: str, default: str | None = None) -> str | None:
    """Get environment variable with optional default value.

    Args:
        key: Environment variable name
        default: Default value if not set

    Returns:
        Environment variable value or default
    """
    return os.getenv(key, default)


# =============================================================================
# Pytest Configuration
# =============================================================================

def pytest_addoption(parser: pytest.Parser) -> None:
    """Add custom command-line options for tests.

    These options allow flexible test configuration without modifying
    environment variables.
    """
    parser.addoption(
        "--redis-url",
        action="store",
        default=None,
        help="Redis connection URL (overrides REDIS_URL env var)",
    )
    parser.addoption(
        "--scrapyd-url",
        action="store",
        default=None,
        help="Scrapyd URL (overrides SCRAPYD_URL env var)",
    )
    parser.addoption(
        "--spider",
        action="store",
        default="allmpus",
        help="Spider name to test",
    )
    parser.addoption(
        "--keyword",
        action="store",
        default="acetone",
        help="Search keyword for testing",
    )
    parser.addoption(
        "--wait-time",
        action="store",
        type=int,
        default=30,
        help="Wait time for job completion in seconds",
    )
    # Scrapyd service management options
    parser.addoption(
        "--skip-scrapyd-start",
        action="store_true",
        default=False,
        help="Skip Scrapyd tests entirely",
    )
    parser.addoption(
        "--scrapyd-already-running",
        action="store_true",
        default=False,
        help="Assume Scrapyd is already running (don't auto-start)",
    )


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def project_root() -> Path:
    """Return the project root directory path.

    Returns:
        Path to project root directory
    """
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def redis_url(request: pytest.FixtureRequest) -> str:
    """Get Redis URL from command line option or environment variable.

    Priority:
        1. --redis-url command line option
        2. REDIS_URL environment variable
        3. Default test value

    Returns:
        Redis connection URL string
    """
    cmd_url = request.config.getoption("--redis-url")
    if cmd_url:
        return cmd_url
    return get_env_var("REDIS_URL", "redis://192.168.4.246:6380/2")


@pytest.fixture(scope="function")
def redis_client(redis_url: str) -> Generator[Redis, None, None]:
    """Create a Redis client for testing.

    This fixture creates a fresh Redis client for each test and
    automatically cleans up test keys after the test completes.

    Args:
        redis_url: Redis connection URL from redis_url fixture

    Yields:
        Redis client instance

    Example:
        def test_something(redis_client):
            redis_client.set("mykey", "value")
            assert redis_client.get("mykey") == "value"
    """
    client = redis.from_url(redis_url, decode_responses=True)
    test_keys: set[str] = set()

    # Store reference to original methods for cleanup tracking
    original_set = client.set

    def tracking_set(key: str, *args, **kwargs) -> bool:
        """Wrap set() to track test keys for cleanup."""
        if key.startswith("test:"):
            test_keys.add(key)
        return original_set(key, *args, **kwargs)

    client.set = tracking_set  # type: ignore

    try:
        yield client
    finally:
        # Cleanup: remove all test keys created during the test
        for key in test_keys:
            try:
                client.delete(key)
            except redis.RedisError:
                pass  # Ignore cleanup errors
        client.close()


@pytest.fixture(scope="session")
def scrapyd_url(request: pytest.FixtureRequest) -> str:
    """Get Scrapyd URL from command line option or environment variable.

    Priority:
        1. --scrapyd-url command line option
        2. SCRAPYD_URL environment variable
        3. Default local test value

    Returns:
        Scrapyd URL string
    """
    cmd_url = request.config.getoption("--scrapyd-url")
    if cmd_url:
        return cmd_url
    return get_env_var("SCRAPYD_URL", "http://127.0.0.1:6800")


@pytest.fixture(scope="session")
def scrapyd_project() -> str:
    """Get Scrapyd project name from environment variable.

    Note: Scrapyd uses 'default' as the default project name when deploying
    locally. The project name in scrapy.cfg is for reference only.

    Returns:
        Project name string
    """
    return get_env_var("SCRAPYD_PROJECT", "default") or "default"


@pytest.fixture(scope="function")
def task_id() -> str:
    """Generate a unique task ID for testing.

    Returns:
        Unique task ID string with 'test-' prefix
    """
    return f"test-{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="session")
def test_spider(request: pytest.FixtureRequest) -> str:
    """Get spider name from command line option or environment variable.

    Returns:
        Spider name string
    """
    cmd_spider = request.config.getoption("--spider")
    if cmd_spider:
        return cmd_spider
    return get_env_var("TEST_SPIDER", "allmpus") or "allmpus"


@pytest.fixture(scope="session")
def test_keyword(request: pytest.FixtureRequest) -> str:
    """Get test keyword from command line option or environment variable.

    Returns:
        Search keyword string
    """
    cmd_keyword = request.config.getoption("--keyword")
    if cmd_keyword:
        return cmd_keyword
    return get_env_var("TEST_KEYWORD", "acetone") or "acetone"


@pytest.fixture(scope="session")
def wait_time(request: pytest.FixtureRequest) -> int:
    """Get wait time for job completion from command line option.

    Returns:
        Wait time in seconds
    """
    cmd_wait = request.config.getoption("--wait-time")
    if cmd_wait is not None:
        return cmd_wait
    return int(get_env_var("TEST_WAIT_TIME", "30") or "30")


# =============================================================================
# Markers
# =============================================================================

def pytest_configure(config: pytest.Config) -> None:
    """Configure custom markers for test categorization."""
    config.addinivalue_line(
        "markers", "redis: marks tests that require Redis connection"
    )
    config.addinivalue_line(
        "markers", "scrapyd: marks tests that require Scrapyd service"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "spider: marks tests that run actual spiders"
    )
