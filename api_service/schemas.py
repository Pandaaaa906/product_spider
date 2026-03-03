"""
API Service Pydantic Models

统一的请求和响应模型定义
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ProductPackage(BaseModel):
    """产品规格包装信息"""

    brand: str
    cat_no: str
    cat_no_unit: str | None = None
    package: str | None = None
    cost: str | None = None
    price: str | None = None
    currency: str | None = None
    delivery_time: str | None = None
    stock_num: str | None = None
    info: str | None = None
    purity: str | None = None
    attrs: dict[str, Any] | None = None


class Product(BaseModel):
    """产品信息"""

    brand: str
    parent: str | None = None
    cat_no: str
    en_name: str | None = None
    chs_name: str | None = None
    cas: str | None = None
    smiles: str | None = None
    mf: str | None = None
    mw: str | None = None
    purity: str | None = None
    appearance: str | None = None
    img_url: str | None = None
    info1: str | None = None
    info2: str | None = None
    info3: str | None = None
    info4: str | None = None
    info5: str | None = None
    tags: str | None = None
    grade: str | None = None
    mol_text: str | None = None
    prd_url: str | None = None
    mdl: str | None = None
    einecs: str | None = None
    shipping_group: str | None = None
    shipping_info: str | None = None
    attrs: dict[str, Any] | None = None
    packages: list[ProductPackage] = []


class SpiderRequest(BaseModel):
    """启动爬虫请求（异步模式）"""

    project: str | None = Field(None, description="项目名称，默认使用 default")
    spider_name: str = Field(..., description="爬虫名称")
    keyword: str | None = Field(None, description="搜索关键词")
    search_params: dict[str, Any] | None = Field(None, description="额外搜索参数")
    task_id: str | None = Field(None, description="任务ID（可选，如果不提供会自动生成）")
    callback_url: str | None = Field(None, description="回调URL（可选）")


class SpiderRunSyncRequest(BaseModel):
    """启动爬虫请求（同步模式，等待结果）"""

    project: str | None = Field(None, description="项目名称，默认使用 default")
    spider_name: str = Field(..., description="爬虫名称")
    keyword: str | None = Field(None, description="搜索关键词")
    search_params: dict[str, Any] | None = Field(None, description="额外搜索参数")
    task_id: str | None = Field(None, description="任务ID（可选，如果不提供会自动生成）")
    timeout: int = Field(60, description="等待结果的超时时间（秒），默认60秒")
    poll_interval: float = Field(2.0, description="轮询间隔（秒），默认2秒")


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
    results: list[Product]
    total: int
    message: str


class SpiderRunSyncResponse(BaseModel):
    """同步运行爬虫响应（包含结果）"""

    task_id: str
    status: str
    message: str
    spider_name: str
    keyword: str | None = None
    results: list[Product] = []
    total_results: int = 0
    wait_time: float = 0.0  # 实际等待时间（秒）
    timed_out: bool = False  # 是否超时


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
