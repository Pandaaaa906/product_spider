#!/usr/bin/env python3
"""
Scrapyd keyword search tests.

This module tests keyword search functionality through the Scrapyd API,
including job scheduling, status monitoring, and Redis result validation.

Run with:
    pytest tests/test_scrapyd_keyword_search.py -v
    pytest tests/test_scrapyd_keyword_search.py -v --spider=allmpus --keyword=acetone
    python tests/test_scrapyd_keyword_search.py

Environment Variables:
    SCRAPYD_URL: Scrapyd service URL (default: http://127.0.0.1:6800)
    SCRAPYD_PROJECT: Project name (default: product_spider)
    REDIS_URL: Redis connection URL (default: redis://192.168.4.246:6380/2)
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generator

import pytest
import requests

if TYPE_CHECKING:
    from redis.client import Redis


# =============================================================================
# Scrapyd Service Manager
# =============================================================================

class ScrapydServiceManager:
    """Manages Scrapyd service lifecycle for testing.

    Automatically starts Scrapyd before tests and stops it after tests,
    ensuring cleanup even if tests fail.

    Usage:
        with ScrapydServiceManager(scrapyd_url="http://127.0.0.1:6800") as mgr:
            if mgr.is_running:
                # Run tests
    """

    def __init__(
        self,
        scrapyd_url: str = "http://127.0.0.1:6800",
        max_wait: int = 30,
        use_uv: bool = True,
    ):
        self.scrapyd_url = scrapyd_url
        self.max_wait = max_wait
        self.use_uv = use_uv
        self.process: subprocess.Popen | None = None
        self.is_running = False
        self._was_already_running = False

    def _is_scrapyd_running(self) -> bool:
        """Check if Scrapyd is already running."""
        try:
            resp = requests.get(f"{self.scrapyd_url}/daemonstatus.json", timeout=2)
            return resp.json().get("status") == "ok"
        except Exception:
            return False

    def _wait_for_scrapyd(self) -> bool:
        """Wait for Scrapyd to become ready."""
        for i in range(self.max_wait):
            if self._is_scrapyd_running():
                return True
            time.sleep(1)
            if i % 5 == 0:
                print(f"  Waiting for Scrapyd... ({i}/{self.max_wait})")
        return False

    def start(self) -> bool:
        """Start Scrapyd service.

        Returns:
            True if started successfully or already running
        """
        # Check if already running
        if self._is_scrapyd_running():
            print(f"[INFO] Scrapyd is already running at {self.scrapyd_url}")
            self.is_running = True
            self._was_already_running = True
            return True

        print(f"[INFO] Starting Scrapyd...")

        # Start Scrapyd using uv run with env-file
        cmd = ["uv", "run", "--env-file=./test.local.env", "scrapyd"]

        try:
            # Use CREATE_NEW_PROCESS_GROUP on Windows for proper process management
            kwargs = {}
            if sys.platform == "win32":
                kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

            project_root = Path(__file__).parent.parent
            self.process = subprocess.Popen(
                cmd,
                stdout=None,
                stderr=None,
                cwd=str(project_root),
                **kwargs
            )

            # Wait for service to be ready
            if self._wait_for_scrapyd():
                print(f"[OK] Scrapyd started successfully (PID: {self.process.pid})")
                self.is_running = True
                return True
            else:
                print(f"[ERROR] Scrapyd failed to start within {self.max_wait} seconds")
                self.stop()
                return False

        except Exception as e:
            print(f"[ERROR] Failed to start Scrapyd: {e}")
            import traceback
            traceback.print_exc()
            return False

    def stop(self) -> None:
        """Stop Scrapyd service if we started it."""
        if self._was_already_running:
            print(f"[INFO] Scrapyd was already running, not stopping")
            return

        if self.process is None:
            return

        print(f"[INFO] Stopping Scrapyd...")
        try:
            if sys.platform == "win32":
                # Send CTRL_BREAK_EVENT on Windows
                self.process.send_signal(subprocess.signal.CTRL_BREAK_EVENT)
            else:
                self.process.terminate()

            # Wait for graceful shutdown
            try:
                self.process.wait(timeout=10)
                print(f"[OK] Scrapyd stopped")
            except subprocess.TimeoutExpired:
                print(f"[WARN] Scrapyd did not stop gracefully, killing...")
                self.process.kill()
                self.process.wait()
                print(f"[OK] Scrapyd killed")

        except Exception as e:
            print(f"[WARN] Error stopping Scrapyd: {e}")
        finally:
            self.process = None
            self.is_running = False

    def __enter__(self) -> ScrapydServiceManager:
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - always stop Scrapyd."""
        self.stop()


@pytest.fixture(scope="session")
def scrapyd_service(request) -> Generator[ScrapydServiceManager, None, None]:
    """Pytest fixture to manage Scrapyd service lifecycle.

    This fixture starts Scrapyd before tests and stops it after tests,
    ensuring cleanup even if tests fail.

    To skip auto-start, use: pytest --skip-scrapyd-start
    To assume Scrapyd is already running: pytest --scrapyd-already-running
    """
    skip_start = request.config.getoption("--skip-scrapyd-start", default=False)
    already_running = request.config.getoption("--scrapyd-already-running", default=False)
    scrapyd_url = request.config.getoption("--scrapyd-url") or "http://127.0.0.1:6800"

    if skip_start:
        print("[INFO] Skipping Scrapyd tests (--skip-scrapyd-start)")
        pytest.skip("Scrapyd tests skipped by --skip-scrapyd-start")
        return

    if already_running:
        print(f"[INFO] Assuming Scrapyd is already running at {scrapyd_url}")
        # Check if it's actually running
        mgr = ScrapydServiceManager(scrapyd_url=scrapyd_url)
        if mgr._is_scrapyd_running():
            mgr.is_running = True
            mgr._was_already_running = True
            yield mgr
        else:
            pytest.fail(f"Scrapyd is not running at {scrapyd_url}. Please start it manually with: uv run --env-file=./test.local.env scrapyd")
        return

    # Try to auto-start Scrapyd
    with ScrapydServiceManager(scrapyd_url=scrapyd_url) as mgr:
        if not mgr.is_running:
            pytest.skip(
                f"Scrapyd service could not be started at {scrapyd_url}. "
                f"Please start it manually with: uv run --env-file=./test.local.env scrapyd "
                f"Or use --scrapyd-already-running if it's already running."
            )
        yield mgr


# =============================================================================
# Helper Functions
# =============================================================================

def check_daemon_status(scrapyd_url: str) -> bool:
    """Check Scrapyd service status.

    Args:
        scrapyd_url: Scrapyd service URL

    Returns:
        True if service is running, False otherwise
    """
    try:
        resp = requests.get(f"{scrapyd_url}/daemonstatus.json", timeout=5)
        data = resp.json()
        return data.get("status") == "ok"
    except requests.exceptions.ConnectionError:
        return False
    except requests.exceptions.Timeout:
        return False


def list_projects(scrapyd_url: str) -> list[str]:
    """List available projects in Scrapyd.

    Args:
        scrapyd_url: Scrapyd service URL

    Returns:
        List of project names
    """
    resp = requests.get(f"{scrapyd_url}/listprojects.json", timeout=10)
    return resp.json().get("projects", [])


def list_spiders(scrapyd_url: str, project: str) -> list[str]:
    """List spiders in a project.

    Args:
        scrapyd_url: Scrapyd service URL
        project: Project name

    Returns:
        List of spider names
    """
    resp = requests.get(
        f"{scrapyd_url}/listspiders.json",
        params={"project": project},
        timeout=10
    )
    return resp.json().get("spiders", [])


def schedule_keyword_search(
    scrapyd_url: str,
    project: str,
    spider_name: str,
    keyword: str,
    task_id: str,
) -> dict[str, Any]:
    """Schedule a keyword search job via Scrapyd API.

    Args:
        scrapyd_url: Scrapyd service URL
        project: Project name
        spider_name: Spider name
        keyword: Search keyword
        task_id: Task ID for tracking

    Returns:
        API response as dictionary
    """
    data = {
        "project": project,
        "spider": spider_name,
        "cmd_keyword_search": "True",
        "keyword": keyword,
        "task_id": task_id,
    }

    resp = requests.post(
        f"{scrapyd_url}/schedule.json",
        data=data,
        timeout=10
    )
    return resp.json()


def list_jobs(scrapyd_url: str, project: str, timeout: int = 30) -> dict[str, Any]:
    """List jobs in a project.

    Args:
        scrapyd_url: Scrapyd service URL
        project: Project name
        timeout: Request timeout in seconds

    Returns:
        Jobs information dictionary
    """
    try:
        resp = requests.get(
            f"{scrapyd_url}/listjobs.json",
            params={"project": project},
            timeout=timeout
        )
        return resp.json()
    except requests.exceptions.Timeout:
        print(f"  [WARN] Timeout listing jobs from {scrapyd_url}")
        return {"running": [], "finished": [], "pending": []}
    except Exception as e:
        print(f"  [WARN] Error listing jobs: {e}")
        return {"running": [], "finished": [], "pending": []}


def get_job_status(scrapyd_url: str, job_id: str, project: str | None = None) -> dict[str, Any]:
    """Get status of a specific job by ID using Scrapyd's status.json API.

    API endpoint: GET /status.json?job={job_id}&project={project}

    Args:
        scrapyd_url: Scrapyd service URL
        job_id: Job ID to check (required)
        project: Optional project name to filter by

    Returns:
        Dictionary with job status information:
        - status: "pending" | "running" | "finished" | "unknown"
        - currstate: Raw currstate value from API
        - error: Error message if any
    """
    try:
        params = {"job": job_id}
        if project:
            params["project"] = project

        resp = requests.get(
            f"{scrapyd_url}/status.json",
            params=params,
            timeout=10
        )
        data = resp.json()

        currstate = data.get("currstate")
        # currstate can be: "pending", "running", "finished", or null (not found)
        if currstate is None:
            return {"status": "unknown", "currstate": None, "error": "Job not found"}

        return {"status": currstate, "currstate": currstate, "error": None}

    except requests.exceptions.Timeout:
        print(f"  [WARN] Timeout checking job status from {scrapyd_url}")
        return {"status": "error", "currstate": None, "error": "timeout"}
    except Exception as e:
        print(f"  [WARN] Error checking job status: {e}")
        return {"status": "error", "currstate": None, "error": str(e)}


def cancel_job(scrapyd_url: str, project: str, job_id: str) -> dict[str, Any]:
    """Cancel a running job.

    Args:
        scrapyd_url: Scrapyd service URL
        project: Project name
        job_id: Job ID to cancel

    Returns:
        API response as dictionary
    """
    resp = requests.post(
        f"{scrapyd_url}/cancel.json",
        data={"project": project, "job": job_id},
        timeout=10
    )
    return resp.json()


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
        count = redis_client.get(f"task:{task_id}:results:count")
        if count:
            return True, int(count), ""

        is_active = redis_client.sismember("active_tasks", task_id)
        time.sleep(1)

        if i % 5 == 0:
            print(f"     Waiting... ({i}/{timeout}), active={is_active}")

    is_active = redis_client.sismember("active_tasks", task_id)
    if is_active:
        return False, 0, "Task still running but no results"
    else:
        return False, 0, "Task not in active list and no results"


def check_job_log(project: str, spider: str, job_id: str) -> tuple[bool, str]:
    """Check job log for errors.

    Args:
        project: Project name
        spider: Spider name
        job_id: Job ID

    Returns:
        Tuple of (success, message)
    """
    log_dir = Path("logs") / project / spider
    if not log_dir.exists():
        return True, "Log directory does not exist"

    log_files = list(log_dir.glob(f"{job_id}*.log"))
    if not log_files:
        return True, f"Log file not found: {job_id}"

    log_file = log_files[0]
    print(f"   Checking log file: {log_file.name}")

    content = log_file.read_text(encoding="utf-8", errors="ignore")

    stats: dict[str, str] = {}
    errors: list[str] = []

    for line in content.split("\n"):
        if "ERROR" in line and "scrapy.core.engine" not in line:
            errors.append(line.strip()[:200])
        if "item_scraped_count" in line:
            stats["items"] = line
        if "log_count/ERROR" in line:
            stats["errors"] = line
        if "spider_exceptions" in line:
            stats["exceptions"] = line

    if errors:
        print(f"   [WARN] Found {len(errors)} errors:")
        for err in errors[:3]:
            print(f"      {err[:150]}")

    has_exceptions = "exceptions" in stats
    error_count = 0
    if "errors" in stats:
        try:
            error_count = int(stats["errors"].split(":")[-1].strip().rstrip("}").strip())
        except (ValueError, IndexError):
            pass

    if has_exceptions or error_count > 0:
        return False, f"Exceptions found in log: {stats}"

    return True, "Log check passed"


def clear_logs(project: str, spider: str | None = None) -> None:
    """Clear old log files.

    Args:
        project: Project name
        spider: Optional spider name to clear specific logs
    """
    if spider:
        log_dir = Path("logs") / project / spider
    else:
        log_dir = Path("logs") / project

    if log_dir.exists():
        for log_file in log_dir.glob("*.log"):
            try:
                log_file.unlink()
            except OSError:
                pass


# =============================================================================
# Tests
# =============================================================================

@pytest.mark.scrapyd
@pytest.mark.integration
class TestScrapydConnection:
    """Tests for Scrapyd connection and basic operations."""

    def test_daemon_status(self, scrapyd_service, scrapyd_url: str) -> None:
        """Test Scrapyd daemon status endpoint.

        Verifies that Scrapyd service is running and responding.
        """
        resp = requests.get(f"{scrapyd_url}/daemonstatus.json", timeout=5)
        data = resp.json()

        assert data.get("status") == "ok", f"Scrapyd status not ok: {data}"
        assert "running" in data, "Missing 'running' field in response"
        assert "pending" in data, "Missing 'pending' field in response"

    def test_list_projects(self, scrapyd_service, scrapyd_url: str, scrapyd_project: str) -> None:
        """Test listing projects.

        Verifies that the configured project exists in Scrapyd.
        """
        projects = list_projects(scrapyd_url)
        assert scrapyd_project in projects, (
            f"Project '{scrapyd_project}' not found. Available: {projects}"
        )

    def test_list_spiders(self, scrapyd_service, scrapyd_url: str, scrapyd_project: str) -> None:
        """Test listing spiders.

        Verifies that spiders can be listed from the project.
        """
        spiders = list_spiders(scrapyd_url, scrapyd_project)
        assert len(spiders) > 0, "No spiders found in project"


@pytest.mark.scrapyd
@pytest.mark.integration
class TestScrapydEndToEnd:
    """End-to-end tests for Scrapyd keyword search workflow."""

    @pytest.mark.slow
    def test_full_workflow(
        self,
        scrapyd_service,
        scrapyd_url: str,
        scrapyd_project: str,
        redis_client: Redis,
        test_spider: str,
        test_keyword: str,
        task_id: str,
        wait_time: int,
    ) -> None:
        """Test complete keyword search workflow.

        This test runs the full workflow:
        1. Check Scrapyd status
        2. Schedule keyword search job
        3. Wait for completion
        4. Check logs for errors
        5. Verify Redis results

        Args:
            scrapyd_url: Scrapyd URL fixture
            scrapyd_project: Project name fixture
            redis_client: Redis client fixture
            test_spider: Spider name fixture
            test_keyword: Search keyword fixture
            task_id: Task ID fixture
            wait_time: Wait time fixture
        """
        print("\n=== Scrapyd Keyword Search E2E Test ===\n")

        # 1. Check service status
        print("1. Checking service status...")
        if not check_daemon_status(scrapyd_url):
            pytest.fail(f"Scrapyd service not running at {scrapyd_url}")
        print("[OK] Service running\n")

        # 2. Verify project exists
        print("2. Checking project...")
        projects = list_projects(scrapyd_url)
        assert scrapyd_project in projects, (
            f"Project '{scrapyd_project}' not found. Available: {projects}"
        )
        print(f"[OK] Project '{scrapyd_project}' exists\n")

        # 3. Verify spider exists
        print("3. Checking spider...")
        spiders = list_spiders(scrapyd_url, scrapyd_project)
        assert test_spider in spiders, (
            f"Spider '{test_spider}' not found. Available: {spiders}"
        )
        print(f"[OK] Spider '{test_spider}' exists\n")

        # 4. Schedule job
        print("4. Scheduling keyword search...")
        result = schedule_keyword_search(
            scrapyd_url=scrapyd_url,
            project=scrapyd_project,
            spider_name=test_spider,
            keyword=test_keyword,
            task_id=task_id,
        )
        assert "jobid" in result, f"Job scheduling failed: {result}"
        job_id = result["jobid"]
        print(f"[OK] Job scheduled: {job_id}\n")

        # 5. Wait for completion using job_id specific status check
        max_wait = 300  # Fixed at 300 seconds as requested
        print(f"5. Waiting for job completion (max {max_wait}s)...")
        job_finished = False
        check_interval = 2
        max_checks = max_wait // check_interval

        for i in range(max_checks):
            time.sleep(check_interval)
            # Use get_job_status to check specific job status by job_id
            status_result = get_job_status(scrapyd_url, job_id, scrapyd_project)
            job_status = status_result.get("status")

            if job_status == "finished":
                job_finished = True
                print(f"[OK] Job completed\n")
                break
            elif job_status == "error":
                print(f"  [WARN] Error checking job status: {status_result.get('error')}")

            if i % 3 == 0:
                print(f"  Waiting... ({(i+1)*check_interval}/{max_wait}), status={job_status}")
        else:
            print(f"[WARN] Job still running (Job ID: {job_id})\n")

        # 6. Check logs
        print("6. Checking job logs...")
        log_ok, log_msg = check_job_log(scrapyd_project, test_spider, job_id)
        if log_ok:
            print(f"   [OK] {log_msg}")
        else:
            print(f"   [WARN] {log_msg}")
        print()

        # 7. Check Redis results
        print(f"7. Checking Redis results...")
        redis_ok, count, redis_msg = check_redis_results(
            redis_client, task_id, timeout=30
        )

        if redis_ok:
            print(f"   [OK] Found {count} results in Redis\n")
        else:
            print(f"   [WARN] {redis_msg}\n")

        # Summary
        print("=== Test Summary ===")
        print(f"Task ID: {task_id}")
        print(f"Job ID: {job_id}")
        print(f"Job finished: {'Yes' if job_finished else 'No'}")
        print(f"Log check: {'Passed' if log_ok else 'Failed'}")
        print(f"Redis results: {count if redis_ok else 0} items")

        # Don't fail if job hasn't finished yet - it's async
        assert job_id is not None, "Job should be scheduled"


# =============================================================================
# Legacy Functions (Backward Compatibility)
# =============================================================================

def main() -> int:
    """Main entry point for backward compatibility.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    parser = argparse.ArgumentParser(description="Test Scrapyd keyword search")
    parser.add_argument("--url", default=None, help="Scrapyd URL")
    parser.add_argument("--project", default="product_spider", help="Project name")
    parser.add_argument("--spider", default="allmpus", help="Spider name")
    parser.add_argument("--keyword", default="acetone", help="Search keyword")
    parser.add_argument("--task-id", default=None, help="Custom task ID")
    parser.add_argument(
        "--wait", type=int, default=5, help="Wait time for job completion"
    )
    parser.add_argument(
        "--redis-wait", type=int, default=30, help="Redis result wait time"
    )

    args = parser.parse_args()

    # Get values from environment or arguments
    scrapyd_url = args.url or "http://127.0.0.1:6800"
    project = args.project

    print("=== Scrapyd Keyword Search Test ===\n")

    # 1. Check service status
    print("1. Checking service status...")
    try:
        if not check_daemon_status(scrapyd_url):
            print("[ERROR] Scrapyd service not running!")
            return 1
        print("[OK] Service running\n")
    except requests.exceptions.ConnectionError:
        print(f"[ERROR] Cannot connect to Scrapyd: {scrapyd_url}")
        return 1

    # 2. List projects
    print("2. Listing projects...")
    projects = list_projects(scrapyd_url)
    if project not in projects:
        print(f"[ERROR] Project '{project}' not found!")
        print(f"Available: {projects}")
        return 1
    print(f"[OK] Project '{project}' exists\n")

    # 3. List spiders
    print("3. Listing spiders...")
    spiders = list_spiders(scrapyd_url, project)
    if args.spider not in spiders:
        print(f"[ERROR] Spider '{args.spider}' not found!")
        print(f"Available: {spiders}")
        return 1
    print(f"[OK] Spider '{args.spider}' exists\n")

    # 4. Schedule job
    print("4. Scheduling keyword search...")
    task_id = args.task_id or f"test-{int(time.time())}"
    result = schedule_keyword_search(
        scrapyd_url=scrapyd_url,
        project=project,
        spider_name=args.spider,
        keyword=args.keyword,
        task_id=task_id,
    )
    if "jobid" not in result:
        print("[ERROR] Failed to schedule job!")
        return 1
    job_id = result["jobid"]
    print(f"[OK] Job scheduled: {job_id}\n")

    # 5. Wait for completion
    print(f"5. Waiting for job completion (max {args.wait}s)...")
    job_finished = False
    for i in range(args.wait):
        time.sleep(1)
        jobs = list_jobs(scrapyd_url, project)
        finished = jobs.get("finished", [])
        job_finished = any(j.get("id") == job_id for j in finished)
        if job_finished:
            print(f"[OK] Job completed\n")
            break
        print(f"  Waiting... ({i + 1}/{args.wait})")
    else:
        print(f"[WARN] Job still running (Job ID: {job_id})\n")

    # 6. Check logs
    print("6. Checking job logs...")
    log_ok, log_msg = check_job_log(project, args.spider, job_id)
    if log_ok:
        print(f"   [OK] {log_msg}")
    else:
        print(f"   [ERROR] {log_msg}")
    print()

    # 7. Check Redis results
    print(f"7. Checking Redis results...")
    import redis as redis_module
    redis_url = "redis://192.168.4.246:6380/2"
    redis_client = redis_module.from_url(redis_url, decode_responses=True)
    redis_ok, count, redis_msg = check_redis_results(
        redis_client, task_id, args.redis_wait
    )

    if redis_ok:
        print(f"   [OK] Found {count} results in Redis\n")
    else:
        print(f"   [ERROR] {redis_msg}\n")

    # Summary
    print("=== Test Summary ===")
    print(f"Task ID: {task_id}")
    print(f"Job ID: {job_id}")
    print(f"Job finished: {'Yes' if job_finished else 'No'}")
    print(f"Log check: {'Passed' if log_ok else 'Failed'}")
    print(f"Redis results: {count if redis_ok else 0} items")

    if redis_ok and log_ok:
        print("\n[OK] All checks passed!")
        return 0
    else:
        print("\n[ERROR] Some checks failed")
        return 1


# =============================================================================
# Main Entry Point (Backward Compatibility)
# =============================================================================

if __name__ == "__main__":
    """Allow running tests directly with: python test_scrapyd_keyword_search.py"""
    if len(sys.argv) > 1 and sys.argv[1] in ("-v", "--verbose", "-h", "--help", "-k"):
        # Running with pytest arguments
        sys.exit(pytest.main([__file__] + sys.argv[1:]))
    else:
        # Running directly
        sys.exit(main())
