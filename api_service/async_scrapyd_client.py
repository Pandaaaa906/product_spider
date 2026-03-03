"""
AsyncScrapydClient - 异步 Scrapyd API 客户端

对接 Scrapyd 的所有 HTTP API 方法：
- daemonstatus.json - 获取守护进程状态
- schedule.json - 启动爬虫任务
- cancel.json - 取消爬虫任务
- listprojects.json - 列出所有项目
- listversions.json - 列出项目所有版本
- listspiders.json - 列出项目所有爬虫
- listjobs.json - 列出项目所有任务
- delversion.json - 删除项目版本
- delproject.json - 删除项目
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from api_service.schemas import (
    ScrapydJobsResponse,
    ScrapydProjectListResponse,
    ScrapydScheduleResponse,
    ScrapydSpiderListResponse,
    ScrapydStatusResponse,
)

logger = logging.getLogger(__name__)


class AsyncScrapydClient:
    """异步 Scrapyd HTTP API 客户端"""

    def __init__(self, base_url: str = "http://localhost:6800", timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        """关闭 HTTP 客户端"""
        await self.client.aclose()

    async def daemon_status(self) -> ScrapydStatusResponse:
        """
        获取 Scrapyd 守护进程状态

        Returns:
            ScrapydStatusResponse: 包含运行中、等待中、已完成任务数量
        """
        response = await self.client.get(f"{self.base_url}/daemonstatus.json")
        response.raise_for_status()
        data = response.json()
        return ScrapydStatusResponse(**data)

    async def schedule(
        self,
        project: str,
        spider: str,
        settings: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> ScrapydScheduleResponse:
        """
        调度（启动）一个爬虫任务

        Args:
            project: 项目名称
            spider: 爬虫名称
            settings: 额外的 Scrapy 设置
            **kwargs: 传递给爬虫的参数

        Returns:
            ScrapydScheduleResponse: 包含任务状态和新任务的 jobid
        """
        data: dict[str, Any] = {"project": project, "spider": spider}

        if settings:
            for key, value in settings.items():
                data[f"setting"] = f"{key}={value}"

        for key, value in kwargs.items():
            data[key] = str(value)

        logger.debug(f"Scheduling spider with data: {data}")
        response = await self.client.post(f"{self.base_url}/schedule.json", data=data)
        response.raise_for_status()
        result = response.json()

        if result.get("status") != "ok":
            raise ScrapydAPIError(f"Failed to schedule spider: {result}")

        return ScrapydScheduleResponse(**result)

    async def cancel(self, project: str, job: str) -> dict[str, Any]:
        """
        取消一个运行中的任务

        Args:
            project: 项目名称
            job: 任务 ID (jobid)

        Returns:
            包含前一个状态和当前状态的字典
        """
        data = {"project": project, "job": job}
        response = await self.client.post(f"{self.base_url}/cancel.json", data=data)
        response.raise_for_status()
        return response.json()

    async def list_projects(self) -> ScrapydProjectListResponse:
        """
        列出所有已部署的项目

        Returns:
            ScrapydProjectListResponse: 包含项目列表
        """
        response = await self.client.get(f"{self.base_url}/listprojects.json")
        response.raise_for_status()
        data = response.json()
        return ScrapydProjectListResponse(**data)

    async def list_versions(self, project: str) -> dict[str, Any]:
        """
        列出项目的所有版本

        Args:
            project: 项目名称

        Returns:
            包含版本列表的字典
        """
        params = {"project": project}
        response = await self.client.get(
            f"{self.base_url}/listversions.json", params=params
        )
        response.raise_for_status()
        return response.json()

    async def list_spiders(self, project: str) -> ScrapydSpiderListResponse:
        """
        列出项目中的所有爬虫

        Args:
            project: 项目名称

        Returns:
            ScrapydSpiderListResponse: 包含爬虫名称列表
        """
        params = {"project": project}
        response = await self.client.get(
            f"{self.base_url}/listspiders.json", params=params
        )
        response.raise_for_status()
        data = response.json()
        return ScrapydSpiderListResponse(**data)

    async def list_jobs(self, project: str) -> ScrapydJobsResponse:
        """
        列出项目中的所有任务

        Args:
            project: 项目名称

        Returns:
            ScrapydJobsResponse: 包含等待中、运行中、已完成的任务列表
        """
        params = {"project": project}
        response = await self.client.get(
            f"{self.base_url}/listjobs.json", params=params
        )
        response.raise_for_status()
        data = response.json()
        return ScrapydJobsResponse(**data)

    async def delete_version(self, project: str, version: str) -> dict[str, Any]:
        """
        删除项目的特定版本

        Args:
            project: 项目名称
            version: 版本号

        Returns:
            操作结果
        """
        data = {"project": project, "version": version}
        response = await self.client.post(f"{self.base_url}/delversion.json", data=data)
        response.raise_for_status()
        return response.json()

    async def delete_project(self, project: str) -> dict[str, Any]:
        """
        删除整个项目

        Args:
            project: 项目名称

        Returns:
            操作结果
        """
        data = {"project": project}
        response = await self.client.post(f"{self.base_url}/delproject.json", data=data)
        response.raise_for_status()
        return response.json()

    async def get_log(
        self, project: str, spider: str, job_id: str, offset: int = 0
    ) -> str:
        """
        获取任务日志

        Args:
            project: 项目名称
            spider: 爬虫名称
            job_id: 任务 ID
            offset: 日志偏移量

        Returns:
            日志内容
        """
        url = f"{self.base_url}/logs/{project}/{spider}/{job_id}.log"
        params = {"offset": offset} if offset > 0 else {}
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return response.text

    async def get_items(self, project: str, spider: str, job_id: str) -> str:
        """
        获取任务输出的 items（如果启用了 item feed）

        Args:
            project: 项目名称
            spider: 爬虫名称
            job_id: 任务 ID

        Returns:
            items 内容（通常是 JSON Lines 格式）
        """
        url = f"{self.base_url}/items/{project}/{spider}/{job_id}.jl"
        response = await self.client.get(url)
        response.raise_for_status()
        return response.text


class ScrapydAPIError(Exception):
    """Scrapyd API 错误"""

    pass
