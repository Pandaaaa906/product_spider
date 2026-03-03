"""
API Service - Product Spider Management API

提供 FastAPI 应用和 Scrapyd 客户端用于爬虫任务管理。
"""

from api_service.async_scrapyd_client import AsyncScrapydClient, ScrapydAPIError
from api_service.scrapyd_client import ScrapydClient

__all__ = [
    "AsyncScrapydClient",
    "ScrapydClient",
    "ScrapydAPIError",
]
