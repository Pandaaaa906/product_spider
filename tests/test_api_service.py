"""
API Service 部署测试

使用方法:
    pytest tests/test_api_service.py -v

测试脚本会自动启动 api_service 和 scrapyd 服务
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pytest
import requests

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.service_manager import ServiceManager

# 配置
API_SERVICE_URL = os.getenv("API_SERVICE_URL", "http://localhost:18000")
SCRAPYD_URL = os.getenv("SCRAPYD_URL", "http://localhost:6800")


@pytest.fixture(scope="session")
def services(request):
    """启动所有服务的 pytest fixture"""
    skip_start = request.config.getoption("--skip-service-start", default=False)

    if skip_start:
        print("[INFO] 跳过服务启动 (--skip-service-start)")
        yield None
        return

    with ServiceManager(
        scrapyd_url=SCRAPYD_URL,
        api_url=API_SERVICE_URL,
        max_wait=30,
    ) as mgr:
        if not mgr.all_running:
            pytest.fail(
                f"服务启动失败。请检查:\n"
                f"  1. 端口 8000 和 6800 是否被占用\n"
                f"  2. test.local.env 文件是否存在\n"
                f"  3. 手动启动: uv run --env-file=./test.local.env scrapyd\n"
                f"           uv run uvicorn api_service.main:app --host 0.0.0.0 --port 8000"
            )
        yield mgr


@pytest.fixture
def api_client():
    """API Service 客户端"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    yield session
    session.close()


def test_api_service_health(services, api_client):
    """[1/5] 测试 API Service 健康状态"""
    response = api_client.get(f"{API_SERVICE_URL}/docs")
    assert response.status_code == 200, f"API Service 未响应: {response.status_code}"


def test_scrapyd_health(services, api_client):
    """[2/5] 测试 Scrapyd 健康状态"""
    response = api_client.get(f"{SCRAPYD_URL}/daemonstatus.json")
    assert response.status_code == 200, f"Scrapyd 未响应: {response.status_code}"
    data = response.json()
    assert data.get("status") == "ok"


def test_list_spiders(services, api_client):
    """[3/5] 测试爬虫列表接口"""
    response = api_client.get(f"{API_SERVICE_URL}/api/spiders/list")
    assert response.status_code == 200

    data = response.json()
    assert "spiders" in data
    assert isinstance(data["spiders"], list)
    print(f"\n  获取到 {len(data['spiders'])} 个爬虫")


def test_run_spider(services, api_client):
    """[4/5] 测试启动爬虫任务"""
    task_id = f"test_task_{int(time.time())}"
    payload = {
        "spider_name": "allmpus",
        "keyword": "acetone",
        "task_id": task_id
    }

    response = api_client.post(f"{API_SERVICE_URL}/api/spiders/run", json=payload)
    assert response.status_code == 200, f"启动失败: {response.text}"

    data = response.json()
    assert data["task_id"] == task_id
    assert data["status"] == "running"
    print(f"\n  Task ID: {task_id}")


def test_task_status_and_results(services, api_client):
    """[5/5] 测试任务状态查询和结果接口"""
    task_id = f"test_task_{int(time.time())}"

    # 先启动一个任务
    payload = {
        "spider_name": "allmpus",
        "keyword": "acetone",
        "task_id": task_id
    }
    run_response = api_client.post(f"{API_SERVICE_URL}/api/spiders/run", json=payload)
    assert run_response.status_code == 200

    # 查询状态
    time.sleep(1)
    status_response = api_client.get(f"{API_SERVICE_URL}/api/spiders/status/{task_id}")
    assert status_response.status_code in [200, 404]

    # 查询结果
    result_response = api_client.get(
        f"{API_SERVICE_URL}/api/spiders/result/{task_id}",
        params={"limit": 10}
    )
    assert result_response.status_code == 200
    data = result_response.json()
    assert data["task_id"] == task_id
    assert "results" in data


def main():
    """直接运行测试的入口"""
    print("=" * 60)
    print("API Service 部署测试")
    print("=" * 60)

    with ServiceManager(
        scrapyd_url=SCRAPYD_URL,
        api_url=API_SERVICE_URL,
        max_wait=30,
    ) as services:
        if not services.all_running:
            print("[ERROR] 服务启动失败")
            return 1

        print("\n开始测试...\n")

        # 创建客户端
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})

        tests = [
            ("API Service 健康检查", lambda: test_api_service_health(services, session)),
            ("Scrapyd 健康检查", lambda: test_scrapyd_health(services, session)),
            ("爬虫列表接口", lambda: test_list_spiders(services, session)),
            ("启动爬虫任务", lambda: test_run_spider(services, session)),
            ("任务状态和结果", lambda: test_task_status_and_results(services, session)),
        ]

        passed = 0
        failed = 0

        for name, test_func in tests:
            try:
                print(f"\n[{name}]")
                test_func()
                print(f"  ✓ 通过")
                passed += 1
            except AssertionError as e:
                print(f"  ✗ 失败: {e}")
                failed += 1
            except Exception as e:
                print(f"  ✗ 错误: {e}")
                failed += 1

        session.close()

        print("\n" + "=" * 60)
        print(f"测试结果: {passed} 通过, {failed} 失败")
        print("=" * 60)

        return 0 if failed == 0 else 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("-v", "--verbose", "-h", "--help"):
        # 使用 pytest 运行
        sys.exit(pytest.main([__file__] + sys.argv[1:]))
    else:
        # 直接运行
        sys.exit(main())
