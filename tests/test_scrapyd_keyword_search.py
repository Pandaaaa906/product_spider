#!/usr/bin/env python3
"""测试 keyword_search 功能 - 包含 Redis 结果验证和日志检查"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import requests
import time
import json
import argparse
import os
import redis

SCRAPYD_URL = os.getenv("SCRAPYD_URL", "http://127.0.0.1:6800")
PROJECT = os.getenv("SCRAPYD_PROJECT", "product_spider")
REDIS_URL = os.getenv("REDIS_URL", "redis://192.168.4.246:6380/2")


def get_redis_client():
    """获取 Redis 客户端"""
    return redis.from_url(REDIS_URL, decode_responses=True)


def test_daemon_status(scrapyd_url: str = None):
    """测试 Scrapyd 服务状态"""
    url = scrapyd_url or SCRAPYD_URL
    resp = requests.get(f"{url}/daemonstatus.json")
    print(f"Daemon Status: {resp.json()}")
    return resp.json().get("status") == "ok"


def test_list_projects(scrapyd_url: str = None):
    """测试列出项目"""
    url = scrapyd_url or SCRAPYD_URL
    resp = requests.get(f"{url}/listprojects.json")
    print(f"Projects: {resp.json()}")
    return resp.json().get("projects", [])


def test_list_spiders(scrapyd_url: str, project: str):
    """测试列出爬虫"""
    resp = requests.get(f"{scrapyd_url}/listspiders.json", params={"project": project})
    print(f"Spiders: {resp.json()}")
    return resp.json().get("spiders", [])


def test_keyword_search(scrapyd_url: str, project: str, spider_name="allmpus", keyword="acetone", task_id=None):
    """测试关键词搜索"""
    if task_id is None:
        task_id = f"test-{int(time.time())}"

    data = {
        "project": project,
        "spider": spider_name,
        "cmd_keyword_search": "True",
        "keyword": keyword,
        "task_id": task_id,
    }

    resp = requests.post(f"{scrapyd_url}/schedule.json", data=data)
    result = resp.json()

    print(f"Start Keyword Search: {result}")
    print(f"Task ID: {task_id}")
    print(f"Job ID: {result.get('jobid')}")

    return task_id, result.get("jobid")


def test_list_jobs(scrapyd_url: str, project: str):
    """测试列出任务"""
    resp = requests.get(f"{scrapyd_url}/listjobs.json", params={"project": project})
    print(f"Jobs: {json.dumps(resp.json(), indent=2)}")
    return resp.json()


def test_cancel_job(project, job_id):
    """取消任务"""
    resp = requests.post(
        f"{SCRAPYD_URL}/cancel.json",
        data={"project": project, "job": job_id}
    )
    print(f"Cancel Job: {resp.json()}")
    return resp.json()


def check_redis_results(task_id: str, timeout: int = 30):
    """检查 Redis 中的结果

    Returns:
        tuple: (success: bool, count: int, error_msg: str)
    """
    print(f"   检查 Redis 结果 (task_id: {task_id})...")

    try:
        r = get_redis_client()

        # 等待结果出现
        for i in range(timeout):
            count = r.get(f"task:{task_id}:results:count")
            if count:
                print(f"   [OK] 找到 {count} 条结果")

                # 获取部分结果预览
                results = r.zrange(f"task:{task_id}:results", 0, 2, withscores=False)
                print(f"   前 {min(3, len(results))} 条结果预览:")
                for i, item_json in enumerate(results[:3]):
                    item = json.loads(item_json)
                    print(f"     {i+1}. {item.get('cat_no', 'N/A')} - {item.get('en_name', 'N/A')[:50]}")

                return True, int(count), ""

            # 检查任务是否活跃
            is_active = r.sismember("active_tasks", task_id)
            if not is_active and i > 5:
                # 任务不在活跃列表中，且等待了一段时间
                pass

            time.sleep(1)
            if i % 5 == 0:
                print(f"     等待中... ({i}/{timeout})")

        # 超时，检查活跃任务集合
        is_active = r.sismember("active_tasks", task_id)
        if is_active:
            return False, 0, "任务仍在运行但未产生结果"
        else:
            return False, 0, "任务不在活跃列表中且没有结果"

    except Exception as e:
        return False, 0, f"Redis 检查失败: {e}"


def check_job_log(project: str, spider: str, job_id: str):
    """检查任务日志是否有错误"""
    log_dir = Path("logs") / project / spider
    if not log_dir.exists():
        return True, "日志目录不存在"

    # 查找对应 job_id 的日志文件
    log_files = list(log_dir.glob(f"{job_id}*.log"))
    if not log_files:
        return True, f"未找到日志文件: {job_id}"

    log_file = log_files[0]
    print(f"   检查日志文件: {log_file.name}")

    content = log_file.read_text(encoding='utf-8', errors='ignore')

    # 检查关键指标
    stats = {}
    errors = []

    for line in content.split('\n'):
        if 'ERROR' in line and 'scrapy.core.engine' not in line:
            errors.append(line.strip()[:200])
        if 'item_scraped_count' in line:
            stats['items'] = line
        if 'log_count/ERROR' in line:
            stats['errors'] = line
        if 'spider_exceptions' in line:
            stats['exceptions'] = line

    if errors:
        print(f"   [WARN] 发现 {len(errors)} 个错误:")
        for err in errors[:3]:
            print(f"      {err[:150]}")

    has_exceptions = 'exceptions' in stats
    error_count = 0
    if 'errors' in stats:
        try:
            error_count = int(stats['errors'].split(':')[-1].strip().rstrip('}').strip())
        except:
            pass

    if has_exceptions or error_count > 0:
        return False, f"日志中发现异常: {stats}"

    return True, "日志检查通过"


def main():
    parser = argparse.ArgumentParser(description="Test Scrapyd keyword search")
    parser.add_argument("--url", default=SCRAPYD_URL, help="Scrapyd URL")
    parser.add_argument("--project", default=PROJECT, help="Project name")
    parser.add_argument("--spider", default="allmpus", help="Spider name")
    parser.add_argument("--keyword", default="acetone", help="Search keyword")
    parser.add_argument("--task-id", default=None, help="Custom task ID")
    parser.add_argument("--wait", type=int, default=5, help="Wait time for job completion (seconds)")
    parser.add_argument("--redis-wait", type=int, default=30, help="Redis result wait time (seconds)")

    args = parser.parse_args()

    # 使用局部变量而非 global
    scrapyd_url = args.url
    project = args.project

    print("=== Scrapyd Keyword Search Test ===\n")

    # 1. 检查服务状态
    print("1. 检查服务状态...")
    try:
        if not test_daemon_status(scrapyd_url):
            print("[ERROR] Scrapyd 服务未启动！")
            return 1
        print("[OK] 服务正常\n")
    except requests.exceptions.ConnectionError:
        print(f"[ERROR] 无法连接到 Scrapyd: {scrapyd_url}")
        print("请确保 Scrapyd 服务已启动")
        return 1

    # 2. 列出项目
    print("2. 列出可用项目...")
    projects = test_list_projects(scrapyd_url)
    if project not in projects:
        print(f"[ERROR] 项目 '{project}' 不存在！")
        print(f"可用项目: {projects}")
        return 1
    print(f"[OK] 项目 '{project}' 存在\n")

    # 3. 列出爬虫
    print("3. 列出项目爬虫...")
    spiders = test_list_spiders(scrapyd_url, project)
    if args.spider not in spiders:
        print(f"[ERROR] 爬虫 '{args.spider}' 不存在！")
        print(f"可用爬虫: {spiders}")
        return 1
    print(f"[OK] 爬虫 '{args.spider}' 存在\n")

    # 4. 启动关键词搜索
    print("4. 启动关键词搜索...")
    task_id, job_id = test_keyword_search(scrapyd_url, project, args.spider, args.keyword, args.task_id)
    if not job_id:
        print("[ERROR] 启动任务失败！")
        return 1
    print(f"[OK] 任务已启动\n")

    # 5. 等待并检查状态
    print(f"5. 等待任务执行 (最多 {args.wait} 秒)...")
    job_finished = False
    for i in range(args.wait):
        time.sleep(1)
        jobs = test_list_jobs(scrapyd_url, project)
        running = jobs.get("running", [])
        finished = jobs.get("finished", [])

        # 检查任务是否完成
        job_finished = any(j.get("id") == job_id for j in finished)
        if job_finished:
            print(f"[OK] 任务已完成\n")
            break
        else:
            print(f"  等待中... ({i + 1}/{args.wait})")
    else:
        print(f"[WARN] 任务仍在运行中 (Job ID: {job_id})\n")

    # 6. 检查日志错误
    print("6. 检查任务日志...")
    log_ok, log_msg = check_job_log(project, args.spider, job_id)
    if log_ok:
        print(f"   [OK] {log_msg}")
    else:
        print(f"   [ERROR] {log_msg}")
    print()

    # 7. 检查 Redis 结果
    print(f"7. 检查 Redis 结果 (最多等待 {args.redis_wait} 秒)...")
    redis_ok, count, redis_msg = check_redis_results(task_id, args.redis_wait)

    if redis_ok:
        print(f"   [OK] Redis 中找到 {count} 条结果\n")
    else:
        print(f"   [ERROR] {redis_msg}\n")

    # 汇总
    print("=== 测试结果汇总 ===")
    print(f"Task ID: {task_id}")
    print(f"Job ID: {job_id}")
    print(f"任务完成: {'是' if job_finished else '否'}")
    print(f"日志检查: {'通过' if log_ok else '失败'}")
    print(f"Redis结果: {count if redis_ok else 0} 条")

    if redis_ok and log_ok:
        print("\n[OK] 所有检查通过！")
        return 0
    else:
        print("\n[ERROR] 部分检查失败")
        return 1


if __name__ == "__main__":
    exit(main())
