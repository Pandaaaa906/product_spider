"""
关键词搜索功能测试 - 简化版
使用 uv run --env-file 直接运行爬虫，检查 Redis 结果
"""

import subprocess
import time
import uuid
import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import redis
import os

# 配置
REDIS_URL = os.getenv("REDIS_URL", "redis://192.168.4.246:6380/2")
DEFAULT_KEYWORD = "acetone"
DEFAULT_WAIT = 60  # 等待爬虫完成的最大秒数


def get_redis_client():
    """获取 Redis 客户端"""
    return redis.from_url(REDIS_URL, decode_responses=True)


def run_spider_keyword_search(spider_name: str, keyword: str = None, task_id: str = None) -> dict:
    """
    运行爬虫关键词搜索

    Returns:
        dict: {"task_id": task_id, "returncode": int, "stdout": str, "stderr": str}
    """
    if task_id is None:
        task_id = f"test-{uuid.uuid4().hex[:8]}"
    if keyword is None:
        keyword = DEFAULT_KEYWORD

    cmd = [
        "uv", "run", "--env-file", "./test.local.env",
        "scrapy", "crawl", spider_name,
        "-a", f"cmd_keyword_search=true",
        "-a", f"keyword={keyword}",
        "-a", f"task_id={task_id}",
    ]

    print(f"  执行命令: {' '.join(cmd)}")

    result = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=DEFAULT_WAIT + 30  # 额外缓冲时间
    )

    return {
        "task_id": task_id,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def check_redis_results(task_id: str, timeout: int = 30) -> tuple:
    """
    检查 Redis 中的结果

    Returns:
        tuple: (success: bool, count: int, error_msg: str)
    """
    r = get_redis_client()

    for i in range(timeout):
        # 检查结果数量
        count = r.get(f"task:{task_id}:results:count")
        if count and int(count) > 0:
            return True, int(count), ""

        # 检查任务是否还在活跃列表
        is_active = r.sismember("active_tasks", task_id)

        time.sleep(1)

        if i % 5 == 0:
            print(f"  等待 Redis 结果... ({i}/{timeout}), active={is_active}")

    # 最终检查
    count = r.get(f"task:{task_id}:results:count")
    if count and int(count) > 0:
        return True, int(count), ""

    return False, 0, f"超时未获取到结果 (task_id={task_id})"


def test_spider_keyword_search(spider_name: str) -> bool:
    """测试单个 spider 的关键词搜索"""
    task_id = f"test-{uuid.uuid4().hex[:8]}"

    print(f"\n{'='*60}")
    print(f"测试 Spider: {spider_name}")
    print(f"Task ID: {task_id}")
    print('='*60)

    # 1. 运行爬虫
    print(f"\n1. 运行爬虫 {spider_name}...")
    try:
        result = run_spider_keyword_search(spider_name, task_id=task_id)
    except subprocess.TimeoutExpired:
        print(f"[ERROR] 爬虫运行超时")
        return False
    except Exception as e:
        print(f"[ERROR] 爬虫运行异常: {e}")
        return False

    if result["returncode"] != 0:
        print(f"[ERROR] 爬虫运行失败:")
        print(f"stdout: {result['stdout'][:500]}")
        print(f"stderr: {result['stderr'][:500]}")
        return False

    print(f"[OK] 爬虫运行完成")

    # 2. 检查 Redis 结果
    print(f"\n2. 检查 Redis 结果...")
    success, count, error = check_redis_results(task_id)

    if not success:
        print(f"[ERROR] {error}")
        return False

    print(f"[OK] 找到 {count} 条结果")

    # 3. 预览部分结果
    print(f"\n3. 结果预览:")
    r = get_redis_client()
    results = r.zrange(f"task:{task_id}:results", 0, 2, withscores=False)
    for i, item_json in enumerate(results[:3]):
        import json
        item = json.loads(item_json)
        print(f"  {i+1}. {item.get('cat_no', 'N/A')} - {item.get('en_name', 'N/A')[:50]}")

    print(f"\n{'='*60}")
    print(f"[OK] {spider_name} 测试通过!")
    print('='*60)

    return True


def get_spiders_from_args():
    """从命令行参数获取 spiders 列表"""
    # 支持两种格式：
    # 1. python test_keyword_search.py spider1 spider2 spider3
    # 2. python test_keyword_search.py --spiders spider1,spider2,spider3
    # 3. 环境变量 KEYWORD_SEARCH_SPIDERS=spider1,spider2

    # 首先检查环境变量
    env_spiders = os.getenv("KEYWORD_SEARCH_SPIDERS")
    if env_spiders:
        return [s.strip() for s in env_spiders.split(",") if s.strip()]

    # 然后检查命令行参数
    args = sys.argv[1:]
    if not args:
        return None  # 返回 None 表示需要自动检测

    # 检查是否有 --spiders 参数
    if "--spiders" in args:
        idx = args.index("--spiders")
        if idx + 1 < len(args):
            return [s.strip() for s in args[idx + 1].split(",") if s.strip()]
        return None

    # 否则所有参数都是 spider 名称
    return args


def discover_spiders_with_keyword_search():
    """
    动态发现所有实现了 keyword_search 方法的爬虫

    Returns:
        list: 实现了 keyword_search 的 spider 名称列表
    """
    spiders_dir = PROJECT_ROOT / "product_spider" / "spiders"
    spiders_with_keyword_search = []

    print("[INFO] 正在检测实现了 keyword_search 方法的爬虫...")

    # 遍历所有 spider 文件
    for spider_file in spiders_dir.glob("*_spider.py"):
        spider_name = spider_file.stem.replace("_spider", "")

        try:
            # 动态导入 spider 模块
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                f"product_spider.spiders.{spider_file.stem}",
                spider_file
            )
            module = importlib.util.module_from_spec(spec)

            # 添加必要的路径
            sys.path.insert(0, str(PROJECT_ROOT))

            try:
                spec.loader.exec_module(module)
            finally:
                sys.path.pop(0)

            # 查找 Spider 类
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and
                    hasattr(attr, 'name') and
                    hasattr(attr, 'keyword_search')):

                    # 检查 keyword_search 是否是基类的方法
                    import inspect
                    keyword_search_method = getattr(attr, 'keyword_search', None)
                    if keyword_search_method:
                        # 检查方法是否在当前类中定义（不是继承的）
                        method_defined_in = getattr(keyword_search_method, '__qualname__', '').split('.')[0]
                        if method_defined_in == attr_name:
                            spiders_with_keyword_search.append(attr.name)
                            break

        except Exception as e:
            print(f"  [WARNING] 检测 {spider_name} 失败: {e}")
            continue

    # 过滤掉 name 为 None 的
    spiders_with_keyword_search = [s for s in spiders_with_keyword_search if s is not None]

    print(f"[INFO] 发现 {len(spiders_with_keyword_search)} 个实现了 keyword_search 的爬虫:")
    for name in sorted(spiders_with_keyword_search):
        print(f"  - {name}")

    return sorted(spiders_with_keyword_search)


def main():
    """主函数"""
    print("="*60)
    print("关键词搜索功能测试")
    print("="*60)

    # 获取 spiders 列表
    spiders = get_spiders_from_args()

    if spiders is None:
        # 自动检测
        spiders = discover_spiders_with_keyword_search()
        if not spiders:
            print("[ERROR] 未检测到实现了 keyword_search 方法的爬虫")
            return 1

    print(f"\n[INFO] 将测试以下 {len(spiders)} 个爬虫:")
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

    # 汇总
    print("\n" + "="*60)
    print("测试汇总")
    print("="*60)
    print(f"总计: {len(spiders)}")
    print(f"通过: {passed}")
    print(f"失败: {failed}")

    if failed == 0:
        print("\n[OK] 所有测试通过!")
        return 0
    else:
        print(f"\n[ERROR] {failed} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
