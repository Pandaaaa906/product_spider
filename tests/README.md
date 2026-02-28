# Product Spider Tests

This directory contains pytest-based tests for the product_spider project.

## Test Structure

```
tests/
├── __init__.py                    # Tests package marker
├── conftest.py                    # Shared fixtures and configuration
├── pytest.ini                     # Pytest configuration
├── test_redis_connection.py       # Redis connection tests
├── test_keyword_search.py         # Direct spider keyword search tests
├── test_scrapyd_keyword_search.py # Scrapyd API keyword search tests
└── test_allmpus_keyword.py        # AllmpusSpider specific tests
```

## Running Tests

### Run All Tests

```bash
pytest tests/
```

### Run Specific Test File

```bash
pytest tests/test_redis_connection.py -v
```

### Run Tests by Marker

```bash
# Run only Redis tests
pytest tests/ -m redis -v

# Run only Scrapyd tests
pytest tests/ -m scrapyd -v

# Exclude slow tests
pytest tests/ -m "not slow" -v

# Run only integration tests
pytest tests/ -m integration -v
```

### Run with Custom Parameters

```bash
# Test with specific spider and keyword
pytest tests/test_keyword_search.py -v --spider=allmpus --keyword=acetone

# Test with custom Redis URL
pytest tests/test_redis_connection.py -v --redis-url=redis://localhost:6379/0

# Test with custom Scrapyd URL
pytest tests/test_scrapyd_keyword_search.py -v --scrapyd-url=http://localhost:6800
```

### Direct Execution (Backward Compatible)

All test files can still be run directly:

```bash
python tests/test_redis_connection.py
python tests/test_keyword_search.py allmpus biosynth
python tests/test_scrapyd_keyword_search.py --spider=allmpus --keyword=acetone
```

## Test Markers

| Marker | Description |
|--------|-------------|
| `redis` | Tests requiring Redis connection |
| `scrapyd` | Tests requiring Scrapyd service |
| `slow` | Tests that take a long time (actual spider execution) |
| `integration` | Integration tests |
| `spider` | Tests that run actual spiders |

## Fixtures

### Session-scoped Fixtures

- `project_root` - Path to project root directory
- `redis_url` - Redis connection URL
- `scrapyd_url` - Scrapyd service URL
- `scrapyd_project` - Scrapyd project name
- `test_spider` - Default spider name for testing
- `test_keyword` - Default search keyword for testing
- `wait_time` - Timeout for job completion

### Function-scoped Fixtures

- `redis_client` - Redis client with automatic cleanup
- `task_id` - Unique task ID for each test

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `REDIS_URL` | Redis connection URL | `redis://192.168.4.246:6380/2` |
| `SCRAPYD_URL` | Scrapyd service URL | `http://127.0.0.1:6800` |
| `SCRAPYD_PROJECT` | Scrapyd project name | `product_spider` |
| `TEST_SPIDER` | Default spider for testing | `allmpus` |
| `TEST_KEYWORD` | Default search keyword | `acetone` |
| `TEST_WAIT_TIME` | Job completion wait time | `30` |
| `KEYWORD_SEARCH_SPIDERS` | Comma-separated spider list | Auto-detect |

## Command Line Options

| Option | Description |
|--------|-------------|
| `--redis-url` | Override Redis URL |
| `--scrapyd-url` | Override Scrapyd URL |
| `--spider` | Specify spider name |
| `--keyword` | Specify search keyword |
| `--wait-time` | Specify wait timeout |

## Writing New Tests

Example test structure:

```python
import pytest

@pytest.mark.redis
class TestMyFeature:
    """Tests for my feature."""

    def test_something(self, redis_client):
        """Test that something works."""
        # Arrange
        redis_client.set("test:key", "value")

        # Act
        result = redis_client.get("test:key")

        # Assert
        assert result == "value"
```

## Best Practices

1. **Use markers** - Tag tests with appropriate markers (`@pytest.mark.redis`)
2. **Use fixtures** - Leverage shared fixtures from `conftest.py`
3. **Clean up** - Tests should clean up after themselves (redis_client fixture handles this)
4. **Document** - Include docstrings explaining what each test verifies
5. **Type hints** - Use type annotations for better code clarity
