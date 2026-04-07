#!/usr/bin/env python3
"""
Keyword search tests - Direct spider execution version.

This module tests keyword search functionality by running spiders directly
using subprocess and verifying results in Redis.

Run with:
    pytest tests/test_keyword_search.py -v
    pytest tests/test_keyword_search.py -v --spider=allmpus --keyword=acetone
    python tests/test_keyword_search.py [spider_names...]

Environment Variables:
    REDIS_URL: Redis connection URL
    KEYWORD_SEARCH_KEYWORD: Default search keyword
    KEYWORD_SEARCH_SPIDERS: Comma-separated list of spiders to test
"""

from __future__ import annotations

import importlib.util
import inspect
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from redis.client import Redis


# =============================================================================
# Constants
# =============================================================================

DEFAULT_WAIT = 120  # Maximum seconds to wait for spider completion
DEFAULT_KEYWORD = "acetone"


# =============================================================================
# Helper Functions
# =============================================================================

def run_spider_keyword_search(
    spider_name: str,
    keyword: str | None = None,
    task_id: str | None = None,
    project_root: Path | None = None,
    wait_timeout: int = DEFAULT_WAIT,
) -> dict:
    """Run a spider with keyword search using subprocess.

    Args:
        spider_name: Name of the spider to run
        keyword: Search keyword (default from env or DEFAULT_KEYWORD)
        task_id: Custom task ID (auto-generated if not provided)
        project_root: Project root directory path
        wait_timeout: Maximum time to wait for spider completion

    Returns:
        Dictionary with task_id, returncode, stdout, and stderr

    Raises:
        subprocess.TimeoutExpired: If spider runs longer than wait_timeout
    """
    if task_id is None:
        task_id = f"test-{uuid.uuid4().hex[:8]}"
    if keyword is None:
        keyword = os.getenv("KEYWORD_SEARCH_KEYWORD", DEFAULT_KEYWORD)
    if project_root is None:
        project_root = Path(__file__).parent.parent

    cmd = [
        "uv", "run", "--env-file", "./test.local.env",
        "scrapy", "crawl", spider_name,
        "-a", "cmd_keyword_search=true",
        "-a", f"keyword={keyword}",
        "-a", f"task_id={task_id}",
    ]

    result = subprocess.run(
        cmd,
        cwd=str(project_root),
        capture_output=True,
        text=True,
        timeout=wait_timeout + 30,  # Extra buffer time
    )

    return {
        "task_id": task_id,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def check_redis_results(
    redis_client: Redis,
    task_id: str,
    timeout: int = 30,
) -> tuple[bool, int, str]:
    """Check for results in Redis with polling.

    Args:
        redis_client: Redis client instance
        task_id: Task ID to check
        timeout: Maximum time to wait for results

    Returns:
        Tuple of (success, count, error_message)
    """
    for i in range(timeout):
        # Check result count
        count = redis_client.get(f"task:{task_id}:results:count")
        if count and int(count) > 0:
            return True, int(count), ""

        # Check if task is still active
        is_active = redis_client.sismember("active_tasks", task_id)

        time.sleep(1)

        if i % 5 == 0:
            print(f"  Waiting for Redis results... ({i}/{timeout}), active={is_active}")

    # Final check
    count = redis_client.get(f"task:{task_id}:results:count")
    if count and int(count) > 0:
        return True, int(count), ""

    return False, 0, f"Timeout waiting for results (task_id={task_id})"


def discover_spiders_with_keyword_search(project_root: Path) -> list[str]:
    """Discover all spiders that implement keyword_search method.

    Args:
        project_root: Project root directory path

    Returns:
        List of spider names that have keyword_search implementation
    """
    spiders_dir = project_root / "product_spider" / "spiders"
    spiders_with_keyword_search: list[str] = []

    print("[INFO] Detecting spiders with keyword_search method...")

    for spider_file in spiders_dir.glob("*_spider.py"):
        spider_name = spider_file.stem.replace("_spider", "")

        try:
            spec = importlib.util.spec_from_file_location(
                f"product_spider.spiders.{spider_file.stem}",
                spider_file
            )
            if spec is None or spec.loader is None:
                continue

            module = importlib.util.module_from_spec(spec)

            # Add necessary path
            sys.path.insert(0, str(project_root))
            try:
                spec.loader.exec_module(module)
            finally:
                sys.path.pop(0)

            # Find Spider class
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and hasattr(attr, "name")
                    and hasattr(attr, "keyword_search")
                ):
                    # Check if keyword_search is defined in current class (not inherited)
                    keyword_search_method = getattr(attr, "keyword_search", None)
                    if keyword_search_method:
                        method_defined_in = getattr(
                            keyword_search_method, "__qualname__", ""
                        ).split(".")[0]
                        if method_defined_in == attr_name:
                            if attr.name is not None:
                                spiders_with_keyword_search.append(attr.name)
                            break

        except Exception as e:
            print(f"  [WARNING] Detection failed for {spider_name}: {e}")
            continue

    print(f"[INFO] Found {len(spiders_with_keyword_search)} spiders with keyword_search:")
    for name in sorted(spiders_with_keyword_search):
        print(f"  - {name}")

    return sorted(spiders_with_keyword_search)


def get_spiders_from_args() -> list[str] | None:
    """Parse spider names from command line arguments.

    Supports:
        1. python test_keyword_search.py spider1 spider2
        2. python test_keyword_search.py --spiders spider1,spider2
        3. Environment variable KEYWORD_SEARCH_SPIDERS=spider1,spider2

    Returns:
        List of spider names or None to trigger auto-detection
    """
    # Check environment variable first
    env_spiders = os.getenv("KEYWORD_SEARCH_SPIDERS")
    if env_spiders:
        return [s.strip() for s in env_spiders.split(",") if s.strip()]

    # Parse command line arguments
    args = sys.argv[1:]
    if not args:
        return None  # Trigger auto-detection

    # Check for --spiders argument
    if "--spiders" in args:
        idx = args.index("--spiders")
        if idx + 1 < len(args):
            return [s.strip() for s in args[idx + 1].split(",") if s.strip()]
        return None

    # Otherwise all arguments are spider names
    return args


# =============================================================================
# Tests
# =============================================================================

@pytest.mark.spider
@pytest.mark.slow
@pytest.mark.integration
class TestKeywordSearch:
    """Tests for keyword search functionality."""

    @pytest.fixture(autouse=True)
    def setup_test(self, project_root: Path, redis_client: Redis) -> None:
        """Setup for each test method."""
        self.project_root = project_root
        self.redis_client = redis_client

    def test_spider_keyword_search(
        self,
        test_spider: str,
        test_keyword: str,
        task_id: str,
    ) -> None:
        """Test keyword search for a single spider.

        This test runs the spider with keyword search and verifies
        that results are stored in Redis.

        Args:
            test_spider: Spider name from fixture
            test_keyword: Search keyword from fixture
            task_id: Unique task ID from fixture
        """
        print(f"\n{'='*60}")
        print(f"Testing Spider: {test_spider}")
        print(f"Task ID: {task_id}")
        print('='*60)

        # 1. Run spider
        print(f"\n1. Running spider {test_spider}...")
        try:
            result = run_spider_keyword_search(
                spider_name=test_spider,
                keyword=test_keyword,
                task_id=task_id,
                project_root=self.project_root,
            )
        except subprocess.TimeoutExpired as e:
            pytest.fail(f"Spider execution timed out: {e}")
        except Exception as e:
            pytest.fail(f"Spider execution failed: {e}")

        assert result["returncode"] == 0, (
            f"Spider failed:\nstdout: {result['stdout'][:500]}\n"
            f"stderr: {result['stderr'][:500]}"
        )
        print("[OK] Spider completed")

        # 2. Check Redis results
        print("\n2. Checking Redis results...")
        success, count, error = check_redis_results(
            self.redis_client, task_id, timeout=30
        )
        assert success, f"Redis check failed: {error}"
        print(f"[OK] Found {count} results")

        # 3. Preview results
        print("\n3. Results preview:")
        results = self.redis_client.zrange(
            f"task:{task_id}:results", 0, 2, withscores=False
        )
        for i, item_json in enumerate(results[:3]):
            item = json.loads(item_json)
            cat_no = item.get("cat_no", "N/A")
            en_name = item.get("en_name", "N/A")[:50]
            print(f"  {i+1}. {cat_no} - {en_name}")

        print(f"\n{'='*60}")
        print(f"[OK] {test_spider} test passed!")
        print('='*60)

    @pytest.mark.parametrize("spider_name", ["allmpus"])  # Default test spider
    def test_specific_spider(self, spider_name: str, task_id: str) -> None:
        """Test a specific spider with keyword search.

        This test can be parametrized to run against multiple spiders.

        Args:
            spider_name: Name of spider to test
            task_id: Unique task ID
        """
        self.test_spider_keyword_search(spider_name, DEFAULT_KEYWORD, task_id)


# =============================================================================
# Legacy Functions (Backward Compatibility)
# =============================================================================

def test_spider_keyword_search(spider_name: str) -> bool:
    """Legacy function for backward compatibility.

    Args:
        spider_name: Name of spider to test

    Returns:
        True if test passes, False otherwise
    """
    project_root = Path(__file__).parent.parent

    # Get Redis client
    import redis as redis_module
    redis_url = os.getenv("REDIS_URL", "redis://192.168.4.246:6380/2")
    redis_client = redis_module.from_url(redis_url, decode_responses=True)

    task_id = f"test-{uuid.uuid4().hex[:8]}"
    keyword = os.getenv("KEYWORD_SEARCH_KEYWORD", DEFAULT_KEYWORD)

    print(f"\n{'='*60}")
    print(f"Testing Spider: {spider_name}")
    print(f"Task ID: {task_id}")
    print('='*60)

    # 1. Run spider
    print(f"\n1. Running spider {spider_name}...")
    try:
        result = run_spider_keyword_search(
            spider_name=spider_name,
            keyword=keyword,
            task_id=task_id,
            project_root=project_root,
        )
    except subprocess.TimeoutExpired:
        print("[ERROR] Spider execution timed out")
        return False
    except Exception as e:
        print(f"[ERROR] Spider execution failed: {e}")
        return False

    if result["returncode"] != 0:
        print(f"[ERROR] Spider failed:\nstdout: {result['stdout'][:500]}")
        print(f"stderr: {result['stderr'][:500]}")
        return False

    print("[OK] Spider completed")

    # 2. Check Redis results
    print("\n2. Checking Redis results...")
    success, count, error = check_redis_results(redis_client, task_id, timeout=30)

    if not success:
        print(f"[ERROR] {error}")
        return False

    print(f"[OK] Found {count} results")

    # 3. Preview results
    print("\n3. Results preview:")
    results = redis_client.zrange(f"task:{task_id}:results", 0, 2, withscores=False)
    for i, item_json in enumerate(results[:3]):
        item = json.loads(item_json)
        cat_no = item.get("cat_no", "N/A")
        en_name = item.get("en_name", "N/A")[:50]
        print(f"  {i+1}. {cat_no} - {en_name}")

    print(f"\n{'='*60}")
    print(f"[OK] {spider_name} test passed!")
    print('='*60)

    return True


def main() -> int:
    """Main entry point for backward compatibility.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print("="*60)
    print("Keyword Search Test")
    print("="*60)

    project_root = Path(__file__).parent.parent

    # Get spiders list
    spiders = get_spiders_from_args()

    if spiders is None:
        # Auto-detect
        spiders = discover_spiders_with_keyword_search(project_root)
        if not spiders:
            print("[ERROR] No spiders with keyword_search detected")
            return 1

    print(f"\n[INFO] Will test {len(spiders)} spiders:")
    for name in spiders:
        print(f"  - {name}")
    print()

    passed = 0
    failed = 0

    for spider in spiders:
        if test_spider_keyword_search(spider):
            passed += 1
        else:
            failed += 1

    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    print(f"Total: {len(spiders)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    if failed == 0:
        print("\n[OK] All tests passed!")
        return 0
    else:
        print(f"\n[ERROR] {failed} tests failed")
        return 1


# =============================================================================
# Main Entry Point (Backward Compatibility)
# =============================================================================

if __name__ == "__main__":
    """Allow running tests directly with: python test_keyword_search.py [spiders...]"""
    # Check if running with pytest or directly
    if len(sys.argv) > 1 and sys.argv[1] in ("-v", "--verbose", "-h", "--help", "-k"):
        # Running with pytest arguments
        sys.exit(pytest.main([__file__] + sys.argv[1:]))
    else:
        # Running directly
        sys.exit(main())
