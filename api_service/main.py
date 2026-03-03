from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import uuid
import httpx
from datetime import datetime
import os

app = FastAPI(title="Product Spider API Service", version="1.0.0")

# Scrapyd配置 - 从环境变量读取
SCRAPYD_URLS = os.getenv("SCRAPYD_URLS", "http://localhost:6800").split(",")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# 请求模型
class SpiderRequest(BaseModel):
    spider_name: str = Field(..., description="爬虫名称")
    keyword: Optional[str] = Field(None, description="搜索关键词")
    search_params: Optional[Dict[str, Any]] = Field(None, description="额外搜索参数")
    task_id: Optional[str] = Field(None, description="任务ID（可选，如果不提供会自动生成）")
    callback_url: Optional[str] = Field(None, description="回调URL（可选）")

class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str
    spider_name: str
    keyword: Optional[str] = None

# Scrapyd客户端
class ScrapydClient:
    def __init__(self, urls: list):
        self.urls = urls
        self.client = httpx.AsyncClient(timeout=30)

    async def schedule_spider(self, spider_name: str, args: dict) -> dict:
        """启动爬虫任务"""
        url = self.urls[0]  # 简化处理，实际应该做负载均衡

        data = {
            "project": "default",
            "spider": spider_name,
            "setting": "API_REQUEST=True",
        }

        # 添加参数
        for key, value in args.items():
            data[key] = str(value)

        response = await self.client.post(f"{url}/schedule.json", data=data)

        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to schedule spider")

        return response.json()

    async def close(self):
        await self.client.aclose()

# 全局变量
scrapyd_client = ScrapydClient(SCRAPYD_URLS)

# 全局缓存（实际项目中应该使用Redis）
task_cache = {}

@app.post("/api/spiders/run", response_model=TaskResponse)
async def run_spider(request: SpiderRequest, background_tasks: BackgroundTasks):
    """启动爬虫任务"""

    # 验证任务ID
    task_id = request.task_id or str(uuid.uuid4())

    # 验证爬虫是否存在（这里简化处理，实际应该检查spiders目录）
    if not request.spider_name:
        raise HTTPException(status_code=400, detail="Spider name is required")

    # 构建爬虫参数
    args = {
        "cmd_keyword_search": "True" if request.keyword else "False",
    }

    if request.keyword:
        args["keyword"] = request.keyword
        args["task_id"] = task_id

    if request.search_params:
        for key, value in request.search_params.items():
            args[key] = str(value)

    # 保存任务信息到缓存
    task_cache[task_id] = {
        "spider_name": request.spider_name,
        "keyword": request.keyword,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
        "callback_url": request.callback_url
    }

    try:
        # 启动爬虫
        result = await scrapyd_client.schedule_spider(request.spider_name, args)

        # 更新任务状态
        if "status" in result and result["status"] == "ok":
            task_cache[task_id]["status"] = "running"
            task_cache[task_id]["scrapyd_job_id"] = result.get("jobid")

            # 启动后台任务监控
            background_tasks.add_task(monitor_task, task_id)

            return TaskResponse(
                task_id=task_id,
                status="running",
                message="Spider scheduled successfully",
                spider_name=request.spider_name,
                keyword=request.keyword
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to schedule spider")

    except Exception as e:
        task_cache[task_id]["status"] = "failed"
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/spiders/status/{task_id}", response_model=TaskResponse)
async def get_task_status(task_id: str):
    """获取任务状态"""
    if task_id not in task_cache:
        # 尝试从Redis获取（实现中应该从Redis获取）
        raise HTTPException(status_code=404, detail="Task not found")

    task_info = task_cache[task_id]
    return TaskResponse(
        task_id=task_id,
        status=task_info["status"],
        message="Task status retrieved",
        spider_name=task_info["spider_name"],
        keyword=task_info.get("keyword")
    )

@app.get("/api/spiders/result/{task_id}")
async def get_task_results(task_id: str, limit: int = 100, offset: int = 0):
    """获取任务结果"""
    # 这里需要实现真正的Redis查询
    # 现在返回模拟数据
    return {
        "task_id": task_id,
        "results": [],  # 实际应该从Redis获取
        "total": 0,
        "limit": limit,
        "offset": offset,
        "message": "Results will be available after task completion"
    }

@app.get("/api/spiders/list")
async def list_spiders():
    """获取所有可用的爬虫"""
    # 这里应该从scrapyd获取所有爬虫
    return {
        "spiders": [
            "allmpus",
            "aladdin",
            "usp",
            "solarbio"
        ]
    }

@app.on_event("shutdown")
async def shutdown_event():
    await scrapyd_client.close()

# 后台任务监控
async def monitor_task(task_id: str):
    """监控任务状态"""
    import asyncio

    while True:
        if task_id not in task_cache:
            break

        task_info = task_cache[task_id]

        # 这里应该从Scrapyd获取真实状态
        # 现在模拟状态变化
        if task_info["status"] == "running":
            # 模拟任务完成
            task_cache[task_id]["status"] = "completed"
            task_cache[task_id]["completed_at"] = datetime.utcnow().isoformat()

            # 如果有回调URL，调用回调
            if task_info.get("callback_url"):
                await call_callback(task_info["callback_url"], task_id)

            break

        await asyncio.sleep(5)  # 每5秒检查一次

async def call_callback(callback_url: str, task_id: str):
    """调用回调URL"""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(callback_url, json={
                "task_id": task_id,
                "status": "completed",
                "timestamp": datetime.utcnow().isoformat()
            })
    except Exception as e:
        print(f"Failed to call callback: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)