#!/usr/bin/env python3
"""
测试运行器 Agent - 自动运行测试并分析错误
使用 .venv 虚拟环境，自动管理 scrapyd 服务
"""

import subprocess
import sys
import os
import time
import signal
import argparse
from pathlib import Path
import json
from datetime import datetime
from contextlib import contextmanager

# 设置 Windows 控制台编码
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 配置
PROJECT_ROOT = Path(__file__).parent
TESTS_DIR = PROJECT_ROOT / "tests"
OUTPUT_DIR = PROJECT_ROOT / "claude_outputs"
ENV_FILE = PROJECT_ROOT / "test.local.env"
VENV_PYTHON = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
VENV_UV = PROJECT_ROOT / ".venv" / "Scripts" / "uv.exe"

# 如果虚拟环境不存在，尝试使用系统 uv/python
if not VENV_UV.exists():
    VENV_UV = "uv"
if not VENV_PYTHON.exists():
    VENV_PYTHON = sys.executable


def clear_logs():
    """清空所有爬虫日志文件"""
    logs_dir = PROJECT_ROOT / "logs"
    if not logs_dir.exists():
        return

    print("[INFO] 清空日志文件...")
    count = 0
    for log_file in logs_dir.rglob("*.log"):
        try:
            log_file.unlink()
            count += 1
        except Exception:
            pass
    print(f"[INFO] 已清空 {count} 个日志文件")


def load_env_file():
    """加载环境变量文件"""
    if ENV_FILE.exists():
        print(f"[INFO] 加载环境变量: {ENV_FILE}")
        with open(ENV_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
    else:
        print(f"[WARNING] 环境变量文件不存在: {ENV_FILE}")


@contextmanager
def scrapyd_service():
    """启动 scrapyd 服务的上下文管理器"""
    scrapyd_process = None
    try:
        print("[INFO] 启动 scrapyd 服务...")
        print(f"[INFO] 使用命令: {VENV_UV} run scrapyd")

        # 启动 scrapyd，使用 --env-file 指定环境变量文件
        scrapyd_process = subprocess.Popen(
            [str(VENV_UV), "run", "--env-file", "./test.local.env", "scrapyd"],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
        )

        # 等待服务启动
        max_wait = 10
        for i in range(max_wait):
            time.sleep(1)
            print(f"  等待 scrapyd 启动... ({i+1}/{max_wait})")
            # 检查进程是否还在运行
            if scrapyd_process.poll() is not None:
                stdout, stderr = scrapyd_process.communicate()
                print(f"[ERROR] scrapyd 启动失败")
                if stdout:
                    print(f"stdout: {stdout.decode()[:500]}")
                if stderr:
                    print(f"stderr: {stderr.decode()[:500]}")
                raise RuntimeError("scrapyd 启动失败")

            # 尝试连接检查服务是否就绪
            try:
                import requests
                resp = requests.get("http://127.0.0.1:6800/daemonstatus.json", timeout=2)
                if resp.json().get("status") == "ok":
                    print("[OK] scrapyd 服务已启动")
                    break
            except Exception:
                pass
        else:
            print("[WARNING] scrapyd 启动超时，继续尝试测试...")

        # 等待服务完全就绪
        time.sleep(2)

        yield scrapyd_process

    finally:
        if scrapyd_process:
            print("[INFO] 停止 scrapyd 服务...")
            try:
                if sys.platform == "win32":
                    scrapyd_process.send_signal(signal.CTRL_BREAK_EVENT)
                else:
                    scrapyd_process.terminate()
                scrapyd_process.wait(timeout=30)
                print("[OK] scrapyd 已停止")
            except Exception as e:
                print(f"[WARNING] 停止 scrapyd 时出错: {e}")
                try:
                    scrapyd_process.kill()
                except Exception:
                    pass


def run_test(test_file: str) -> dict:
    """运行单个测试文件

    Args:
        test_file: 测试文件名
    """
    test_path = TESTS_DIR / test_file
    if not test_path.exists():
        return {
            "status": "error",
            "file": test_file,
            "error": f"测试文件不存在: {test_path}"
        }

    print(f"\n{'='*60}")
    print(f"运行测试: {test_file}")
    print('='*60)

    def execute_test():
        """执行测试的实际逻辑"""
        try:
            # 使用 --wait 30 和 --redis-wait 30 等待爬虫完成和结果写入
            result = subprocess.run(
                [str(VENV_PYTHON), str(test_path), "--wait", "30", "--redis-wait", "30"],
                capture_output=True,
                text=True,
                cwd=str(PROJECT_ROOT),
                timeout=180  # 3分钟超时
            )

            output = {
                "status": "success" if result.returncode == 0 else "failed",
                "file": test_file,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "timestamp": datetime.now().isoformat()
            }

            if result.returncode == 0:
                print(f"[OK] {test_file} 测试通过")
            else:
                print(f"[ERROR] {test_file} 测试失败")
                print(f"返回码: {result.returncode}")
                if result.stderr:
                    print(f"错误输出:\n{result.stderr[:500]}")

            return output

        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "file": test_file,
                "error": "测试超时 (3分钟)"
            }
        except Exception as e:
            return {
                "status": "error",
                "file": test_file,
                "error": str(e)
            }

    return execute_test()


def analyze_error(result: dict) -> str:
    """分析错误原因并提出建议"""
    if result["status"] == "success":
        return ""

    stderr = result.get("stderr", "")
    stdout = result.get("stdout", "")
    error_msg = result.get("error", "")
    combined = stderr + stdout + error_msg

    analysis = []

    # 分析常见错误
    if "Connection refused" in combined or "ConnectionError" in combined or \
       "MaxRetryError" in combined or "无法连接" in combined or \
       "WinError 10061" in combined:
        analysis.append("【错误原因】无法连接到 Scrapyd 服务")
        analysis.append("【建议】1. 确保 scrapyd 已正确启动")
        analysis.append("         2. 检查端口 6800 是否被占用")
        analysis.append("         3. 手动启动: uv run scrapyd")

    elif "REDIS_URL not configured" in combined:
        analysis.append("【错误原因】REDIS_URL 环境变量未配置")
        analysis.append("【建议】1. 创建 test.local.env 文件并配置 REDIS_URL")
        analysis.append("         2. 检查 settings.py 中的 REDIS_URL 配置")

    elif "ModuleNotFoundError" in combined or "No module named" in combined:
        module = "未知"
        if "No module named '" in combined:
            try:
                module = combined.split("No module named '")[1].split("'")[0]
            except IndexError:
                pass
        analysis.append(f"【错误原因】缺少 Python 模块: {module}")
        analysis.append(f"【建议】1. 激活虚拟环境: .venv\\Scripts\\activate")
        analysis.append(f"         2. 安装依赖: uv sync")

    elif "ValueError: task_id is required" in combined:
        analysis.append("【错误原因】cmd_keyword_search=True 但没有提供 task_id")
        analysis.append("【建议】在测试代码中添加 task_id 参数")

    elif "项目" in combined and "不存在" in combined:
        analysis.append("【错误原因】Scrapyd 中未部署项目 'product_spider'")
        analysis.append("【建议】1. 部署项目: uv run scrapyd-deploy testing -p product_spider")
        analysis.append("         2. 或检查 SCRAPYD_PROJECT 环境变量配置")

    elif "Spider not found" in combined or "spider not found" in combined.lower():
        analysis.append("【错误原因】爬虫名称错误或爬虫未部署到 Scrapyd")
        analysis.append("【建议】1. 检查爬虫名称拼写")
        analysis.append("         2. 部署项目: uv run scrapyd-deploy testing -p product_spider")

    elif "timeout" in result["status"].lower():
        analysis.append("【错误原因】测试执行超时")
        analysis.append("【建议】1. 检查网络连接")
        analysis.append("         2. 检查目标网站是否可访问")

    elif "scrapyd 启动失败" in combined or "项目部署失败" in combined:
        analysis.append("【错误原因】scrapyd 服务启动或部署失败")
        analysis.append("【建议】1. 检查是否有其他 scrapyd 实例在运行")
        analysis.append("         2. 检查端口 6800 是否被占用")
        analysis.append("         3. 检查 scrapyd-deploy 配置是否正确")
        analysis.append("         4. 手动运行 'uv run scrapyd' 和 'uv run scrapyd-deploy testing -p product_spider' 查看详细错误")

    else:
        analysis.append("【错误原因】未知错误")
        analysis.append(f"【详细信息】{stderr[:300] if stderr else error_msg[:300]}")

    return "\n".join(analysis)


def save_results(results: list):
    """保存测试结果到文件"""
    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_DIR / f"test_result_{timestamp}.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n[INFO] 测试结果已保存: {output_file}")
    return output_file


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

    print(f"[INFO] 发现 {len(spiders_with_keyword_search)} 个实现了 keyword_search 的爬虫")
    for name in sorted(spiders_with_keyword_search):
        print(f"  - {name}")

    return sorted(spiders_with_keyword_search)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="测试运行器 - 自动运行测试并分析错误",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python test_runner.py                          # 运行所有测试（自动检测spiders）
  python test_runner.py --spiders allmpus        # 只测试 allmpus
  python test_runner.py --spiders allmpus,biosynth  # 测试多个 spider
        """
    )
    parser.add_argument(
        "--spiders",
        type=str,
        default=None,
        help="要测试的 spider 列表，用逗号分隔（如：allmpus,biosynth）。不指定则自动检测所有实现了 keyword_search 的爬虫"
    )
    parser.add_argument(
        "--skip-redis-test",
        action="store_true",
        help="跳过 Redis 连接测试"
    )

    args = parser.parse_args()

    print("="*60)
    print("测试运行器 Agent")
    print(f"Python: {VENV_PYTHON}")
    print(f"UV: {VENV_UV}")
    print("="*60)

    # 加载环境变量
    load_env_file()

    # 清空日志文件
    clear_logs()

    # 检查虚拟环境
    if not Path(VENV_PYTHON).exists():
        print(f"[WARNING] 虚拟环境未找到: {VENV_PYTHON}")
        print("[WARNING] 将使用系统 Python")

    # 确定要测试的 spiders
    if args.spiders:
        spiders_to_test = [s.strip() for s in args.spiders.split(",") if s.strip()]
        print(f"\n[INFO] 指定测试 {len(spiders_to_test)} 个爬虫: {', '.join(spiders_to_test)}")
    else:
        spiders_to_test = discover_spiders_with_keyword_search()
        if not spiders_to_test:
            print("\n[ERROR] 未检测到实现了 keyword_search 方法的爬虫")
            sys.exit(1)
        print(f"\n[INFO] 自动检测到 {len(spiders_to_test)} 个实现了 keyword_search 的爬虫")

    # 设置环境变量供 test_keyword_search.py 使用
    os.environ["KEYWORD_SEARCH_SPIDERS"] = ",".join(spiders_to_test)

    # 要运行的测试文件
    test_configs = []
    if not args.skip_redis_test:
        test_configs.append({"file": "test_redis_connection.py"})
    test_configs.append({"file": "test_keyword_search.py"})  # 使用简化版关键词搜索测试

    # 运行测试
    results = []
    for config in test_configs:
        test_file = config["file"]

        result = run_test(test_file)
        results.append(result)

        # 分析错误
        if result["status"] != "success":
            analysis = analyze_error(result)
            print(f"\n[分析] {test_file}")
            print(analysis)
            result["analysis"] = analysis

    # 保存结果
    output_file = save_results(results)

    # 汇总
    print("\n" + "="*60)
    print("测试汇总")
    print("="*60)

    passed = sum(1 for r in results if r["status"] == "success")
    failed = len(results) - passed

    print(f"总计: {len(results)} 个测试")
    print(f"通过: {passed}")
    print(f"失败: {failed}")

    if failed > 0:
        print("\n失败的测试:")
        for r in results:
            if r["status"] != "success":
                print(f"  - {r['file']}: {r['status']}")
        sys.exit(1)
    else:
        print("\n[OK] 所有测试通过!")
        sys.exit(0)


if __name__ == "__main__":
    main()
