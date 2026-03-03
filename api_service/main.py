"""
API Service - Product Spider 管理接口

提供 HTTP API 用于：
- 启动/停止爬虫任务
- 查询任务状态和结果
- 列出可用爬虫
"""

from __future__ import annotations

import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException

from api_service.schemas import (
    ScrapydStatusResponse,
    SpiderListResponse,
    SpiderRequest,
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global scrapyd_client

    # 启动时初始化客户端
    logger.info(f"Initializing ScrapydClient with URLs: {SCRAPYD_URLS}")
    scrapyd_client = ScrapydClient(
        base_url=SCRAPYD_URLS[0],
        redis_url=REDIS_URL,
    )

    # 检查 Redis 连接
    redis_health = await scrapyd_client.check_redis_health()
    logger.info(f"Redis health: {redis_health}")

    yield

    # 关闭时清理资源
    logger.info("Shutting down API Service...")
    if scrapyd_client:
        await scrapyd_client.close()


app = FastAPI(
    title="Product Spider API Service",
    version="1.0.0",
    lifespan=lifespan,
)

# 内存任务缓存（实际应该使用 Redis 或数据库）
task_cache: dict[str, dict[str, Any]] = {}


@app.get("/health")
async def health_check() -> dict[str, Any]:
    """健康检查接口"""
    health = {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

    # 检查 Scrapyd 连接
    try:
        if scrapyd_client:
            scrapyd_status = await scrapyd_client.daemon_status()
            health["scrapyd"] = {
                "status": "ok",
                "running": scrapyd_status.running,
                "pending": scrapyd_status.pending,
            }
    except Exception as e:
        health["scrapyd"] = {"status": "error", "error": str(e)}

    # 检查 Redis 连接
    try:
        if scrapyd_client:
            redis_health = await scrapyd_client.check_redis_health()
            health["redis"] = redis_health
    except Exception as e:
        health["redis"] = {"status": "error", "error": str(e)}

    return health


@app.get("/api/scrapyd/status", response_model=ScrapydStatusResponse)
async def get_scrapyd_status() -> ScrapydStatusResponse:
    """获取 Scrapyd 服务状态"""
    if not scrapyd_client:
        raise HTTPException(status_code=503, detail="Scrapyd client not initialized")

    try:
        return await scrapyd_client.daemon_status()
    except Exception as e:
        logger.error(f"Failed to get Scrapyd status: {e}")
        raise HTTPException(status_code=503, detail=f"Scrapyd unavailable: {e}")


@app.get("/api/scrapyd/projects")
async def list_projects() -> dict[str, Any]:
    """列出所有已部署的项目"""
    if not scrapyd_client:
        raise HTTPException(status_code=503, detail="Scrapyd client not initialized")

    try:
        projects = await scrapyd_client.list_projects()
        return {"status": "ok", "projects": projects.projects}
    except Exception as e:
        logger.error(f"Failed to list projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/scrapyd/spiders/{project}")
async def list_project_spiders(project: str) -> dict[str, Any]:
    """列出项目中的所有爬虫"""
    if not scrapyd_client:
        raise HTTPException(status_code=503, detail="Scrapyd client not initialized")

    try:
        spiders = await scrapyd_client.list_spiders(project)
        return {"status": "ok", "project": project, "spiders": spiders.spiders}
    except Exception as e:
        logger.error(f"Failed to list spiders for {project}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/spiders/list", response_model=SpiderListResponse)
async def list_spiders() -> SpiderListResponse:
    """获取所有可用的爬虫（使用默认项目）"""
    if not scrapyd_client:
        raise HTTPException(status_code=503, detail="Scrapyd client not initialized")

    try:
        spiders = await scrapyd_client.list_spiders(DEFAULT_PROJECT)
        return SpiderListResponse(spiders=spiders.spiders)
    except Exception as e:
        logger.error(f"Failed to list spiders: {e}")
        # 返回硬编码列表作为备用
        return SpiderListResponse(
            spiders=["allmpus", "aladdin", "usp", "solarbio", "tsbiochem"]
        )


@app.post("/api/spiders/run", response_model=TaskResponse)
async def run_spider(
    request: SpiderRequest, background_tasks: BackgroundTasks
) -> TaskResponse:
    """启动爬虫任务"""
    if not scrapyd_client:
        raise HTTPException(status_code=503, detail="Scrapyd client not initialized")

    # 生成或使用提供的任务 ID
    task_id = request.task_id or str(uuid.uuid4())

    # 验证爬虫名称
    if not request.spider_name:
        raise HTTPException(status_code=400, detail="Spider name is required")

    # 使用请求中的项目或默认项目
    project = request.project or DEFAULT_PROJECT

    # 构建爬虫参数
    spider_args: dict[str, Any] = {
        "cmd_keyword_search": "True" if request.keyword else "False",
    }

    if request.keyword:
        spider_args["keyword"] = request.keyword
        spider_args["task_id"] = task_id

    if request.search_params:
        spider_args.update(request.search_params)

    # 保存任务信息
    task_cache[task_id] = {
        "spider_name": request.spider_name,
        "keyword": request.keyword,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
        "callback_url": request.callback_url,
    }

    try:
        # 调度爬虫任务
        result = await scrapyd_client.schedule(
            project=project,
            spider=request.spider_name,
            **spider_args,
        )

        # 更新任务状态
        if result.status == "ok":
            task_cache[task_id]["status"] = "running"
            task_cache[task_id]["scrapyd_job_id"] = result.jobid

            # 启动后台任务监控
            background_tasks.add_task(monitor_task, task_id, result.jobid)

            return TaskResponse(
                task_id=task_id,
                status="running",
                message="Spider scheduled successfully",
                spider_name=request.spider_name,
                keyword=request.keyword,
            )
        else:
            task_cache[task_id]["status"] = "failed"
            raise HTTPException(status_code=500, detail="Failed to schedule spider")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to schedule spider: {e}")
        task_cache[task_id]["status"] = "failed"
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/spiders/status/{task_id}", response_model=TaskResponse)
async def get_task_status(task_id: str) -> TaskResponse:
    """获取任务状态（优先从 Redis 获取）"""
    if not scrapyd_client:
        raise HTTPException(status_code=503, detail="Scrapyd client not initialized")

    # 首先尝试从 Redis 获取状态
    try:
        redis_status = await scrapyd_client.get_task_status_from_redis(task_id)
        if redis_status["status"] != "error":
            # 获取爬虫名称
            spider_name = "unknown"
            if task_id in task_cache:
                spider_name = task_cache[task_id].get("spider_name", "unknown")

            return TaskResponse(
                task_id=task_id,
                status=redis_status["status"],
                message=f"Task has {redis_status['total_count']} results",
                spider_name=spider_name,
                keyword=task_cache.get(task_id, {}).get("keyword"),
            )
    except Exception as e:
        logger.warning(f"Failed to get Redis status for {task_id}: {e}")

    # 回退到内存缓存
    if task_id not in task_cache:
        raise HTTPException(status_code=404, detail="Task not found")

    task_info = task_cache[task_id]
    return TaskResponse(
        task_id=task_id,
        status=task_info["status"],
        message="Task status retrieved from cache",
        spider_name=task_info["spider_name"],
        keyword=task_info.get("keyword"),
    )


@app.get("/api/spiders/result/{task_id}", response_model=TaskResultResponse)
async def get_task_results(
    task_id: str, limit: int = 100, offset: int = 0
) -> TaskResultResponse:
    """获取任务结果（从 Redis 查询）"""
    if not scrapyd_client:
        raise HTTPException(status_code=503, detail="Scrapyd client not initialized")

    try:
        # 从 Redis 获取产品结果
        result_data = await scrapyd_client.get_task_results_from_redis(
            task_id=task_id,
            result_type="product",
            limit=limit,
            offset=offset,
        )

        # 获取任务信息
        task_info = task_cache.get(task_id, {})

        return TaskResultResponse(
            task_id=task_id,
            results=result_data["results"],
            total=result_data["total"],
            limit=limit,
            offset=offset,
            message=result_data.get("error", "Results retrieved successfully"),
        )

    except Exception as e:
        logger.error(f"Failed to get results for {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/spiders/cancel/{task_id}")
async def cancel_task(task_id: str) -> dict[str, Any]:
    """取消运行中的任务"""
    if not scrapyd_client:
        raise HTTPException(status_code=503, detail="Scrapyd client not initialized")

    if task_id not in task_cache:
        raise HTTPException(status_code=404, detail="Task not found")

    task_info = task_cache[task_id]
    job_id = task_info.get("scrapyd_job_id")

    if not job_id:
        raise HTTPException(status_code=400, detail="Task has no associated job ID")

    # 使用任务缓存中的项目或默认项目
    project = task_info.get("project", DEFAULT_PROJECT)

    try:
        result = await scrapyd_client.cancel(project, job_id)

        # 更新缓存状态
        task_cache[task_id]["status"] = "cancelled"

        return {
            "status": "ok",
            "task_id": task_id,
            "job_id": job_id,
            "previous_state": result.get("prevstate"),
        }

    except Exception as e:
        logger.error(f"Failed to cancel task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/jobs/{project}")
async def list_jobs(project: str) -> dict[str, Any]:
    """列出项目的所有任务"""
    if not scrapyd_client:
        raise HTTPException(status_code=503, detail="Scrapyd client not initialized")

    try:
        jobs = await scrapyd_client.list_jobs(project)
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


# 后台任务监控
async def monitor_task(task_id: str, job_id: str) -> None:
    """
    后台任务监控

    定期检查任务状态，更新缓存，调用回调 URL
    """
    import asyncio

    logger.info(f"Starting monitor for task {task_id} (job {job_id})")

    check_count = 0
    max_checks = 720  # 最多检查 720 次（约 1 小时，每 5 秒一次）

    while check_count < max_checks:
        await asyncio.sleep(5)
        check_count += 1

        if task_id not in task_cache:
            logger.warning(f"Task {task_id} not found in cache, stopping monitor")
            break

        task_info = task_cache[task_id]

        # 如果任务已经完成或失败，停止监控
        if task_info["status"] in ("completed", "failed", "cancelled"):
            logger.info(f"Task {task_id} is {task_info['status']}, stopping monitor")
            break

        # 检查 Redis 中是否有结果（表示任务已完成）
        try:
            redis_status = await scrapyd_client.get_task_status_from_redis(task_id)
            if redis_status["total_count"] > 0 and not redis_status["is_active"]:
                # 任务已完成且有结果
                task_cache[task_id]["status"] = "completed"
                task_cache[task_id]["completed_at"] = datetime.utcnow().isoformat()

                # 调用回调 URL
                if task_info.get("callback_url"):
                    await call_callback(task_info["callback_url"], task_id)

                logger.info(f"Task {task_id} completed with results")
                break
        except Exception as e:
            logger.warning(f"Error checking Redis status for {task_id}: {e}")

        # 每 12 次检查（约 1 分钟）查询一次 Scrapyd 任务状态
        if check_count % 12 == 0:
            try:
                project = task_info.get("project", DEFAULT_PROJECT)
                jobs = await scrapyd_client.list_jobs(project)

                # 检查任务是否在 finished 列表中
                job_finished = any(j.id == job_id for j in jobs.finished)

                if job_finished:
                    task_cache[task_id]["status"] = "completed"
                    task_cache[task_id]["completed_at"] = datetime.utcnow().isoformat()

                    if task_info.get("callback_url"):
                        await call_callback(task_info["callback_url"], task_id)

                    logger.info(f"Task {task_id} found in finished jobs")
                    break

            except Exception as e:
                logger.warning(f"Error checking Scrapyd jobs for {task_id}: {e}")

    logger.info(f"Monitor stopped for task {task_id}")


async def call_callback(callback_url: str, task_id: str) -> None:
    """调用回调 URL"""
    import httpx

    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                callback_url,
                json={
                    "task_id": task_id,
                    "status": "completed",
                    "timestamp": datetime.utcnow().isoformat(),
                },
                timeout=10.0,
            )
        logger.info(f"Callback successful for task {task_id}")
    except Exception as e:
        logger.error(f"Failed to call callback for task {task_id}: {e}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
