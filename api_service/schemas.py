"""
API Service Pydantic Models

统一的请求和响应模型定义
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SpiderRequest(BaseModel):
    """启动爬虫请求"""

    project: str | None = Field(None, description="项目名称，默认使用 default")
    spider_name: str = Field(..., description="爬虫名称")
    keyword: str | None = Field(None, description="搜索关键词")
    search_params: dict[str, Any] | None = Field(None, description="额外搜索参数")
    task_id: str | None = Field(None, description="任务ID（可选，如果不提供会自动生成）")
    callback_url: str | None = Field(None, description="回调URL（可选）")


class TaskResponse(BaseModel):
    """任务响应"""

    task_id: str
    status: str
    message: str
    spider_name: str
    keyword: str | None = None


class SpiderListResponse(BaseModel):
    """爬虫列表响应"""

    spiders: list[str]


class TaskResultResponse(BaseModel):
    """任务结果响应"""

    task_id: str
    results: list[dict[str, Any]]
    total: int
    limit: int
    offset: int
    message: str


class ScrapydStatusResponse(BaseModel):
    """Scrapyd 状态响应"""

    status: str
    running: int
    pending: int
    finished: int
    node_name: str


class ScrapydScheduleResponse(BaseModel):
    """Scrapyd 调度响应"""

    status: str
    jobid: str
    node_name: str | None = None


class ScrapydJob(BaseModel):
    """Scrapyd 任务信息"""

    id: str
    spider: str
    pid: int | None = None
    start_time: str | None = None
    end_time: str | None = None


class ScrapydJobsResponse(BaseModel):
    """Scrapyd 任务列表响应"""

    status: str
    pending: list[ScrapydJob]
    running: list[ScrapydJob]
    finished: list[ScrapydJob]


class ScrapydProjectListResponse(BaseModel):
    """Scrapyd 项目列表响应"""

    status: str
    projects: list[str]
    node_name: str | None = None


class ScrapydSpiderListResponse(BaseModel):
    """Scrapyd 爬虫列表响应"""

    status: str
    spiders: list[str]
    node_name: str | None = None
