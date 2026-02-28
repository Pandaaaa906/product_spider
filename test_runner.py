#!/usr/bin/env python3
"""
测试运行器 - 使用 Click Group 重构
支持多个测试命令：redis, keyword, scrapyd, all
"""

import subprocess
import sys
import os
from pathlib import Path
import json
from datetime import datetime
from typing import List, Optional

import click

# 配置
PROJECT_ROOT = Path(__file__).parent
TESTS_DIR = PROJECT_ROOT / "tests"
OUTPUT_DIR = PROJECT_ROOT / "claude_outputs"
ENV_FILE = PROJECT_ROOT / "test.local.env"
VENV_PYTHON = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
VENV_UV = PROJECT_ROOT / ".venv" / "Scripts" / "uv.exe"

if not VENV_UV.exists():
    VENV_UV = "uv"
if not VENV_PYTHON.exists():
    VENV_PYTHON = sys.executable

# 全局选项
pass_config = click.make_pass_decorator(dict, ensure=True)


@click.group()
@click.option('--env-file', type=click.Path(exists=True), default=str(ENV_FILE),
              help='环境变量文件路径')
@click.option('--output-dir', type=click.Path(), default=str(OUTPUT_DIR),
              help='输出目录')
@click.option('--output-json', is_flag=True, help='输出JSON格式结果')
@click.option('--skip-log-clear', is_flag=True, help='跳过清空日志文件')
@click.pass_context
def cli(ctx, env_file, output_dir, output_json, skip_log_clear):
    """
    测试运行器 - 运行各种单元测试

    示例:
        python test_runner.py redis              # 测试Redis连接
        python test_runner.py keyword            # 测试关键词搜索
        python test_runner.py keyword --spiders allmpus  # 指定爬虫
        python test_runner.py scrapyd            # 测试Scrapyd
        python test_runner.py all                # 运行所有测试
    """
    ctx.ensure_object(dict)
    ctx.obj['env_file'] = env_file
    ctx.obj['output_dir'] = Path(output_dir)
    ctx.obj['output_json'] = output_json
    ctx.obj['skip_log_clear'] = skip_log_clear

    # 加载环境变量
    _load_env_file(env_file)

    # 清空日志
    if not skip_log_clear:
        _clear_logs()


def _load_env_file(env_file: str):
    """加载环境变量文件"""
    env_path = Path(env_file)
    if env_path.exists():
        if not click.get_current_context().obj.get('output_json'):
            click.echo(f"[INFO] 加载环境变量: {env_path}")
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value


def _clear_logs():
    """清空所有爬虫日志文件"""
    logs_dir = PROJECT_ROOT / "logs"
    if not logs_dir.exists():
        return

    count = 0
    for log_file in logs_dir.rglob("*.log"):
        try:
            log_file.unlink()
            count += 1
        except Exception:
            pass

    ctx = click.get_current_context()
    if not ctx.obj.get('output_json'):
        click.echo(f"[INFO] 已清空 {count} 个日志文件")


def _discover_spiders() -> List[str]:
    """动态发现所有实现了 keyword_search 方法的爬虫"""
    spiders_dir = PROJECT_ROOT / "product_spider" / "spiders"
    spiders_with_keyword_search = []

    ctx = click.get_current_context()
    if not ctx.obj.get('output_json'):
        click.echo("[INFO] 正在检测实现了 keyword_search 方法的爬虫...")

    for spider_file in spiders_dir.glob("*_spider.py"):
        spider_name = spider_file.stem.replace("_spider", "")

        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                f"product_spider.spiders.{spider_file.stem}",
                spider_file
            )
            module = importlib.util.module_from_spec(spec)
            sys.path.insert(0, str(PROJECT_ROOT))

            try:
                spec.loader.exec_module(module)
            finally:
                sys.path.pop(0)

            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and
                    hasattr(attr, 'name') and
                    hasattr(attr, 'keyword_search')):

                    keyword_search_method = getattr(attr, 'keyword_search', None)
                    if keyword_search_method:
                        method_defined_in = getattr(keyword_search_method, '__qualname__', '').split('.')[0]
                        if method_defined_in == attr_name:
                            if attr.name:
                                spiders_with_keyword_search.append(attr.name)
                            break

        except Exception as e:
            pass

    spiders_with_keyword_search = [s for s in spiders_with_keyword_search if s]

    if not ctx.obj.get('output_json'):
        click.echo(f"[INFO] 发现 {len(spiders_with_keyword_search)} 个实现了 keyword_search 的爬虫")
        for name in sorted(spiders_with_keyword_search):
            click.echo(f"  - {name}")

    return sorted(spiders_with_keyword_search)


def _run_test_file(test_file: str, timeout: int = 300) -> dict:
    """运行单个测试文件"""
    test_path = TESTS_DIR / test_file
    if not test_path.exists():
        return {"status": "error", "file": test_file, "error": f"测试文件不存在: {test_path}"}

    try:
        result = subprocess.run(
            [str(VENV_PYTHON), str(test_path)],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=timeout
        )

        return {
            "status": "success" if result.returncode == 0 else "failed",
            "file": test_file,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    except subprocess.TimeoutExpired:
        return {"status": "timeout", "file": test_file, "error": f"测试超时 ({timeout}秒)"}
    except Exception as e:
        return {"status": "error", "file": test_file, "error": str(e)}


def _save_results(results: list, output_dir: Path) -> Path:
    """保存测试结果"""
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"test_result_{timestamp}.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    return output_file


def _print_result(result: dict):
    """打印测试结果"""
    ctx = click.get_current_context()
    if ctx.obj.get('output_json'):
        return

    if result["status"] == "success":
        click.secho(f"[OK] {result['file']} 测试通过", fg="green")
    else:
        click.secho(f"[ERROR] {result['file']} 测试失败", fg="red")
        if result.get("error"):
            click.echo(f"  {result['error']}")


def _print_summary(results: list):
    """打印测试汇总"""
    ctx = click.get_current_context()
    passed = sum(1 for r in results if r["status"] == "success")
    failed = len(results) - passed

    if ctx.obj.get('output_json'):
        summary = {
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "results": results
        }
        click.echo(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        click.echo("\n" + "="*60)
        click.echo("测试汇总")
        click.echo("="*60)
        click.echo(f"总计: {len(results)} 个测试")
        click.secho(f"通过: {passed}", fg="green" if failed == 0 else None)
        if failed > 0:
            click.secho(f"失败: {failed}", fg="red")

    return failed == 0


# ============ 子命令 ============

@cli.command()
@pass_config
def redis(config):
    """测试 Redis 连接"""
    if not config.get('output_json'):
        click.echo("\n" + "="*60)
        click.echo("测试: Redis 连接")
        click.echo("="*60)

    result = _run_test_file("test_redis_connection.py")
    _print_result(result)

    # 保存结果
    output_file = _save_results([result], config['output_dir'])
    if not config.get('output_json'):
        click.echo(f"\n[INFO] 测试结果已保存: {output_file}")

    # 汇总
    success = _print_summary([result])
    sys.exit(0 if success else 1)


@cli.command()
@click.option('--spiders', help='要测试的爬虫列表，逗号分隔。不指定则自动检测')
@click.option('--keyword', default='acetone', help='搜索关键词')
@pass_config
def keyword(config, spiders, keyword):
    """测试关键词搜索功能"""
    if not config.get('output_json'):
        click.echo("\n" + "="*60)
        click.echo("测试: 关键词搜索")
        click.echo("="*60)

    # 确定要测试的spiders
    if spiders:
        spiders_to_test = [s.strip() for s in spiders.split(",") if s.strip()]
        if not config.get('output_json'):
            click.echo(f"[INFO] 指定测试 {len(spiders_to_test)} 个爬虫: {', '.join(spiders_to_test)}")
    else:
        spiders_to_test = _discover_spiders()
        if not spiders_to_test:
            click.echo("[ERROR] 未检测到实现了 keyword_search 方法的爬虫", err=True)
            sys.exit(1)

    # 设置环境变量
    os.environ["KEYWORD_SEARCH_SPIDERS"] = ",".join(spiders_to_test)
    os.environ["KEYWORD_SEARCH_KEYWORD"] = keyword

    # 运行测试
    result = _run_test_file("test_keyword_search.py", timeout=180)
    _print_result(result)

    # 保存结果
    output_file = _save_results([result], config['output_dir'])
    if not config.get('output_json'):
        click.echo(f"\n[INFO] 测试结果已保存: {output_file}")

    # 汇总
    success = _print_summary([result])
    sys.exit(0 if success else 1)


@cli.command()
@pass_config
def scrapyd(config):
    """测试 Scrapyd 关键词搜索"""
    if not config.get('output_json'):
        click.echo("\n" + "="*60)
        click.echo("测试: Scrapyd 关键词搜索")
        click.echo("="*60)

    result = _run_test_file("test_scrapyd_keyword_search.py", timeout=300)
    _print_result(result)

    # 保存结果
    output_file = _save_results([result], config['output_dir'])
    if not config.get('output_json'):
        click.echo(f"\n[INFO] 测试结果已保存: {output_file}")

    # 汇总
    success = _print_summary([result])
    sys.exit(0 if success else 1)


@cli.command()
@click.option('--spiders', help='要测试的爬虫列表（用于keyword测试），逗号分隔')
@click.option('--keyword', default='acetone', help='搜索关键词')
@click.option('--skip-scrapyd', is_flag=True, help='跳过Scrapyd测试')
@pass_config
def all(config, spiders, keyword, skip_scrapyd):
    """运行所有测试"""
    if not config.get('output_json'):
        click.echo("\n" + "="*60)
        click.echo("测试: 全部测试")
        click.echo("="*60)

    results = []

    # 1. Redis 连接测试
    if not config.get('output_json'):
        click.echo("\n--- Redis 连接测试 ---")
    result = _run_test_file("test_redis_connection.py")
    results.append(result)
    _print_result(result)

    # 2. 关键词搜索测试
    if not config.get('output_json'):
        click.echo("\n--- 关键词搜索测试 ---")

    if spiders:
        spiders_to_test = [s.strip() for s in spiders.split(",") if s.strip()]
    else:
        spiders_to_test = _discover_spiders()

    if spiders_to_test:
        os.environ["KEYWORD_SEARCH_SPIDERS"] = ",".join(spiders_to_test)
        os.environ["KEYWORD_SEARCH_KEYWORD"] = keyword

        result = _run_test_file("test_keyword_search.py", timeout=180)
        results.append(result)
        _print_result(result)

    # 3. Scrapyd 测试
    if not skip_scrapyd:
        if not config.get('output_json'):
            click.echo("\n--- Scrapyd 测试 ---")
        result = _run_test_file("test_scrapyd_keyword_search.py", timeout=300)
        results.append(result)
        _print_result(result)

    # 保存结果
    output_file = _save_results(results, config['output_dir'])
    if not config.get('output_json'):
        click.echo(f"\n[INFO] 测试结果已保存: {output_file}")

    # 汇总
    success = _print_summary(results)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    cli()
