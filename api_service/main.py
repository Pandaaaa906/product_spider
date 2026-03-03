"""
API Service - Product Spider 管理接口

提供 HTTP API 用于：
- 启动/停止爬虫任务
- 查询任务状态和结果
- 列出可用爬虫
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException

from api_service.schemas import (
    ScrapydStatusResponse,
    SpiderListResponse,
    SpiderRequest,
    SpiderRunSyncRequest,
    SpiderRunSyncResponse,
    TaskResponse,
    TaskResultResponse,
)
from api_service.scrapyd_client import ScrapydClient

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# 环境变量配置
SCRAPYD_URLS = os.getenv("SCRAPYD_URLS", "http://localhost:6800").split(",")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DEFAULT_PROJECT = os.getenv("SCRAPYD_PROJECT", "default")

# 全局客户端
scrapyd_client: ScrapydClient | None = None


def get_scrapyd_client() -> ScrapydClient:
    """依赖注入：获取 ScrapydClient，未初始化时抛出 503"""
    if scrapyd_client is None:
        raise HTTPException(status_code=503, detail="Scrapyd client not initialized")
    return scrapyd_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global scrapyd_client

    logger.info(f"Initializing ScrapydClient with URLs: {SCRAPYD_URLS}")
    scrapyd_client = ScrapydClient(
        base_url=SCRAPYD_URLS[0],
        redis_url=REDIS_URL,
    )

    redis_health = await scrapyd_client.check_redis_health()
    logger.info(f"Redis health: {redis_health}")

    yield

    logger.info("Shutting down API Service...")
    if scrapyd_client:
        await scrapyd_client.close()


app = FastAPI(
    title="Product Spider API Service",
    version="1.0.0",
    lifespan=lifespan,
)


# ==================== 辅助函数 ====================


async def schedule_spider_task(
    client: ScrapydClient,
    spider_name: str,
    keyword: str | None = None,
    project: str | None = None,
    task_id: str | None = None,
    search_params: dict[str, Any] | None = None,
) -> tuple[str, str, str]:
    """
    调度爬虫任务

    Args:
        client: Scrapyd 客户端
        spider_name: 爬虫名称
        keyword: 搜索关键词
        project: 项目名称（默认使用 DEFAULT_PROJECT）
        task_id: 任务 ID（可选，自动生成 UUID）
        search_params: 额外搜索参数

    Returns:
        (actual_task_id, actual_project, job_id): 实际任务ID、项目名称、Scrapyd job ID

    Raises:
        HTTPException: 调度失败时抛出
    """
    # 生成任务ID和确定项目名称
    actual_task_id = task_id or str(uuid.uuid4())
    actual_project = project or DEFAULT_PROJECT

    # 构建爬虫参数列表
    args: list[tuple[str, str]] = [("cmd_keyword_search", "True"), ("task_id", actual_task_id)]
    if keyword:
        args.append(("keyword", keyword))
    if search_params:
        args.append(("search_params", ','.join((f"{k}={v}"for k, v in search_params))))

    # 调度任务
    try:
        result = await client.schedule(
            project=actual_project,
            spider=spider_name,
            args=args,
        )

        if result.status != "ok":
            raise HTTPException(status_code=500, detail="Failed to schedule spider")

        return actual_task_id, actual_project, result.jobid

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to schedule spider: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def check_task_completion(
    task_id: str,
    client: ScrapydClient,
) -> tuple[bool, int]:
    """
    检查任务是否完成（仅检查 Redis 状态）

    Args:
        task_id: 任务 ID
        client: Scrapyd 客户端

    Returns:
        (is_completed, total_count)
    """
    try:
        # 检查 Redis 状态
        redis_status = await client.get_task_status_from_redis(task_id)

        if redis_status["status"] == "completed":
            return True, redis_status.get("total_count", 0)

        # 任务未完成，返回当前结果数量
        return False, redis_status.get("total_count", 0)

    except Exception as e:
        logger.warning(f"Error checking task completion for {task_id}: {e}")
        return False, 0


async def fetch_task_results(
    task_id: str,
    client: ScrapydClient,
) -> dict[str, Any]:
    """获取任务结果"""
    try:
        result_data = await client.get_task_results_from_redis(
            task_id=task_id,
        )
        return result_data
    except Exception as e:
        logger.error(f"Failed to get results for {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def call_callback(callback_url: str, task_id: str) -> None:
    """调用回调 URL"""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                callback_url,
                json={
                    "task_id": task_id,
                    "status": "completed",
                    "timestamp": datetime.now(UTC).isoformat(),
                },
                timeout=10.0,
            )
        logger.info(f"Callback successful for task {task_id}")
    except Exception as e:
        logger.error(f"Failed to call callback for task {task_id}: {e}")


# ==================== API 端点 ====================


@app.get("/health")
async def health_check(
    client: ScrapydClient = Depends(get_scrapyd_client),
) -> dict[str, Any]:
    """健康检查接口"""
    health = {"status": "ok", "timestamp": datetime.now(UTC).isoformat()}

    try:
        scrapyd_status = await client.daemon_status()
        health["scrapyd"] = {
            "status": "ok",
            "running": scrapyd_status.running,
            "pending": scrapyd_status.pending,
        }
    except Exception as e:
        health["scrapyd"] = {"status": "error", "error": str(e)}

    try:
        redis_health = await client.check_redis_health()
        health["redis"] = redis_health
    except Exception as e:
        health["redis"] = {"status": "error", "error": str(e)}

    return health


@app.get("/api/scrapyd/status", response_model=ScrapydStatusResponse)
async def get_scrapyd_status(
    client: ScrapydClient = Depends(get_scrapyd_client),
) -> ScrapydStatusResponse:
    """获取 Scrapyd 服务状态"""
    try:
        return await client.daemon_status()
    except Exception as e:
        logger.error(f"Failed to get Scrapyd status: {e}")
        raise HTTPException(status_code=503, detail=f"Scrapyd unavailable: {e}")


@app.get("/api/scrapyd/projects")
async def list_projects(
    client: ScrapydClient = Depends(get_scrapyd_client),
) -> dict[str, Any]:
    """列出所有已部署的项目"""
    try:
        projects = await client.list_projects()
        return {"status": "ok", "projects": projects.projects}
    except Exception as e:
        logger.error(f"Failed to list projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/scrapyd/spiders/{project}")
async def list_project_spiders(
    project: str,
    client: ScrapydClient = Depends(get_scrapyd_client),
) -> dict[str, Any]:
    """列出项目中的所有爬虫"""
    try:
        spiders = await client.list_spiders(project)
        return {"status": "ok", "project": project, "spiders": spiders.spiders}
    except Exception as e:
        logger.error(f"Failed to list spiders for {project}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/spiders/list", response_model=SpiderListResponse)
async def list_spiders(
    client: ScrapydClient = Depends(get_scrapyd_client),
) -> SpiderListResponse:
    """获取所有可用的爬虫（使用默认项目）"""
    try:
        spiders = await client.list_spiders(DEFAULT_PROJECT)
        return SpiderListResponse(spiders=spiders.spiders)
    except Exception as e:
        logger.error(f"Failed to list spiders: {e}")
        return SpiderListResponse(
            spiders=["allmpus", "aladdin", "usp", "solarbio", "tsbiochem"]
        )


@app.post("/api/spiders/run", response_model=TaskResponse)
async def run_spider(
    request: SpiderRequest,
    background_tasks: BackgroundTasks,
    client: ScrapydClient = Depends(get_scrapyd_client),
) -> TaskResponse:
    """
    异步启动爬虫任务，立即返回任务 ID

    此接口不会等待任务完成，而是立即返回任务 ID。
    适合长时间运行的任务或不需要即时结果的场景。
    """
    # 调度任务
    task_id, project, job_id = await schedule_spider_task(
        client=client,
        spider_name=request.spider_name,
        keyword=request.keyword,
        project=request.project,
        task_id=request.task_id,
        search_params=request.search_params,
    )

    # 如果有回调URL，启动后台监控
    if request.callback_url:
        background_tasks.add_task(
            monitor_task,
            task_id,
            job_id,
            project,
            request.callback_url,
            client,
        )

    return TaskResponse(
        task_id=task_id,
        status="running",
        message="Spider scheduled successfully",
        spider_name=request.spider_name,
        keyword=request.keyword,
    )


@app.post("/api/spiders/run/sync", response_model=SpiderRunSyncResponse)
async def run_spider_sync(
    request: SpiderRunSyncRequest,
    client: ScrapydClient = Depends(get_scrapyd_client),
) -> SpiderRunSyncResponse:
    """
    同步运行爬虫任务，等待结果返回

    此接口会阻塞直到任务完成或达到超时时间。
    适用于需要即时获取结果的场景。
    """
    start_time = time.time()

    # 调度任务
    task_id, project, job_id = await schedule_spider_task(
        client=client,
        spider_name=request.spider_name,
        keyword=request.keyword,
        project=request.project,
        task_id=request.task_id,
        search_params=request.search_params,
    )

    logger.info(
        f"Sync task {task_id} started (job {job_id}), "
        f"waiting up to {request.timeout}s"
    )

    # 等待结果或超时
    elapsed = 0.0
    poll_count = 0

    while elapsed < request.timeout:
        await asyncio.sleep(request.poll_interval)
        elapsed = time.time() - start_time
        poll_count += 1

        # 检查任务是否完成
        is_completed, total_count = await check_task_completion(
            task_id,
            client,
        )

        if is_completed:
            # 获取结果
            result_data = await fetch_task_results(task_id, client)
            results = result_data["results"]
            total_count = result_data["total"]
            logger.info(
                f"Sync task {task_id} completed with "
                f"{total_count} results in {elapsed:.2f}s"
            )
            return SpiderRunSyncResponse(
                task_id=task_id,
                status="completed",
                message=f"Task completed with {total_count} results",
                spider_name=request.spider_name,
                keyword=request.keyword,
                results=results,
                total_results=total_count,
                wait_time=elapsed,
                timed_out=False,
            )

    # 超时
    logger.info(
        f"Sync task {task_id} timed out after {elapsed:.2f}s, "
        f"collected partial results"
    )

    # 尝试获取已收集的部分结果
    try:
        result_data = await fetch_task_results(task_id, client)
        results = result_data["results"]
        total_count = result_data["total"]
    except Exception as e:
        logger.error(f"Failed to get partial results: {e}")
        results = []
        total_count = 0

    return SpiderRunSyncResponse(
        task_id=task_id,
        status="running",
        message=f"Timeout after {request.timeout}s, collected {total_count} results so far",
        spider_name=request.spider_name,
        keyword=request.keyword,
        results=results,
        total_results=total_count,
        wait_time=elapsed,
        timed_out=True,
    )


@app.get("/api/spiders/status/{task_id}", response_model=TaskResponse)
async def get_task_status(
    task_id: str,
    client: ScrapydClient = Depends(get_scrapyd_client),
) -> TaskResponse:
    """获取任务状态（优先从 Redis 获取）"""
    # 从 Redis 获取状态
    try:
        redis_status = await client.get_task_status_from_redis(task_id)
        if redis_status["status"] != "error":
            return TaskResponse(
                task_id=task_id,
                status=redis_status["status"],
                message=f"Task has {redis_status['total_count']} results",
                spider_name="unknown",
                keyword=None,
            )
    except Exception as e:
        logger.warning(f"Failed to get Redis status for {task_id}: {e}")

    raise HTTPException(status_code=404, detail="Task not found")


@app.get("/api/spiders/result/{task_id}", response_model=TaskResultResponse)
async def get_task_results(
    task_id: str,
    client: ScrapydClient = Depends(get_scrapyd_client),
) -> TaskResultResponse:
    """获取任务结果（从 Redis 查询）"""
    result_data = await client.get_task_results_from_redis(task_id=task_id)

    return TaskResultResponse(
        task_id=task_id,
        results=result_data["results"],
        total=result_data["total"],
        message=result_data.get("error", "Results retrieved successfully"),
    )


@app.post("/api/spiders/cancel/{job_id}")
async def cancel_task(
    job_id: str,
    project: str = DEFAULT_PROJECT,
    client: ScrapydClient = Depends(get_scrapyd_client),
) -> dict[str, Any]:
    """取消运行中的任务"""
    try:
        result = await client.cancel(project, job_id)

        return {
            "status": "ok",
            "job_id": job_id,
            "project": project,
            "previous_state": result.get("prevstate"),
        }
    except Exception as e:
        logger.error(f"Failed to cancel job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/jobs/{project}")
async def list_jobs(
    project: str = "default",
    client: ScrapydClient = Depends(get_scrapyd_client),
) -> dict[str, Any]:
    """列出项目的所有任务"""
    try:
        jobs = await client.list_jobs(project)
        return {
            "status": "ok",
            "project": project,
            "pending": [{"id": j.id, "spider": j.spider} for j in jobs.pending],
            "running": [
                {
                    "id": j.id,
                    "spider": j.spider,
                    "pid": j.pid,
                    "start_time": j.start_time,
                }
                for j in jobs.running
            ],
            "finished": [
                {
                    "id": j.id,
                    "spider": j.spider,
                    "start_time": j.start_time,
                    "end_time": j.end_time,
                }
                for j in jobs.finished
            ],
        }
    except Exception as e:
        logger.error(f"Failed to list jobs for {project}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 后台任务监控 ====================


async def monitor_task(
    task_id: str,
    job_id: str,
    project: str,
    callback_url: str,
    client: ScrapydClient,
) -> None:
    """
    后台任务监控 - 仅在有 callback_url 时启动

    定期检查任务状态，完成后调用回调 URL
    """
    logger.info(f"Starting monitor for task {task_id} (job {job_id})")

    check_count = 0
    max_checks = 720  # 最多检查 720 次（约 1 小时，每 5 秒一次）

    while check_count < max_checks:
        await asyncio.sleep(5)
        check_count += 1

        # 检查任务是否完成
        is_completed, _ = await check_task_completion(
            task_id,
            client,
        )

        if is_completed:
            await call_callback(callback_url, task_id)
            logger.info(f"Task {task_id} completed, callback triggered")
            break

    logger.info(f"Monitor stopped for task {task_id}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
