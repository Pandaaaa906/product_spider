"""
ScrapydClient - 带 Redis 结果获取功能的 Scrapyd 客户端

继承自 AsyncScrapydClient，添加从 Redis 获取爬虫任务结果的功能
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import redis

from api_service.async_scrapyd_client import AsyncScrapydClient
from api_service.schemas import (
    ScrapydJobsResponse,
    ScrapydProjectListResponse,
    ScrapydScheduleResponse,
    ScrapydSpiderListResponse,
    ScrapydStatusResponse,
)

logger = logging.getLogger(__name__)


class ScrapydClient(AsyncScrapydClient):
    """带 Redis 支持的 Scrapyd 客户端"""

    # Redis key 前缀
    TASK_RESULTS_PREFIX = "CMD_KEYWORD_SEARCH:{task_id}:results"
    TASK_PRODUCTS_PREFIX = "CMD_KEYWORD_SEARCH:{task_id}:results:product"
    TASK_PACKAGES_PREFIX = "CMD_KEYWORD_SEARCH:{task_id}:results:package"

    def __init__(
        self,
        base_url: str = "http://localhost:6800",
        timeout: float = 30.0,
        redis_url: str | None = None,
    ):
        super().__init__(base_url, timeout)
        self.redis_url = redis_url or os.getenv(
            "REDIS_URL", "redis://localhost:6379/0"
        )
        self._redis_client: redis.Redis | None = None

    @property
    def redis_client(self) -> redis.Redis:
        """获取 Redis 客户端（延迟初始化）"""
        if self._redis_client is None:
            self._redis_client = redis.from_url(
                self.redis_url, decode_responses=True
            )
        return self._redis_client

    async def get_task_results_from_redis(
        self,
        task_id: str,
        result_type: str = "product",
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """
        从 Redis 获取任务结果

        Args:
            task_id: 任务 ID
            result_type: 结果类型 ('product' 或 'package')
            limit: 返回结果数量限制
            offset: 结果偏移量

        Returns:
            包含结果列表、总数等信息的字典
        """
        try:
            # 构建 Redis key
            if result_type == "product":
                key = self.TASK_PRODUCTS_PREFIX.format(task_id=task_id)
                count_key = f"{key}:count"
            elif result_type == "package":
                key = self.TASK_PACKAGES_PREFIX.format(task_id=task_id)
                count_key = f"{key}:count"
            else:
                # 通用结果 key
                key = self.TASK_RESULTS_PREFIX.format(task_id=task_id)
                count_key = f"task:{task_id}:results:count"

            logger.debug(f"Fetching results from Redis key: {key}")

            # 获取总数
            total_str = self.redis_client.get(count_key)
            total = int(total_str) if total_str else 0

            # 获取结果列表 (sorted set)
            results_data = self.redis_client.zrange(
                key, offset, offset + limit - 1, withscores=False
            )

            # 解析 JSON 结果
            results = []
            for item in results_data:
                try:
                    if isinstance(item, str):
                        results.append(json.loads(item))
                    else:
                        results.append(json.loads(item.decode("utf-8")))
                except (json.JSONDecodeError, AttributeError) as e:
                    logger.warning(f"Failed to parse result item: {e}")
                    continue

            return {
                "task_id": task_id,
                "results": results,
                "total": total,
                "limit": limit,
                "offset": offset,
                "result_type": result_type,
            }

        except redis.ConnectionError as e:
            logger.error(f"Redis connection error: {e}")
            return {
                "task_id": task_id,
                "results": [],
                "total": 0,
                "limit": limit,
                "offset": offset,
                "error": "Redis connection failed",
            }
        except Exception as e:
            logger.error(f"Error fetching results from Redis: {e}")
            return {
                "task_id": task_id,
                "results": [],
                "total": 0,
                "limit": limit,
                "offset": offset,
                "error": str(e),
            }

    async def get_task_status_from_redis(self, task_id: str) -> dict[str, Any]:
        """
        从 Redis 获取任务状态

        Args:
            task_id: 任务 ID

        Returns:
            包含任务状态的字典
        """
        try:
            # 检查活跃任务集合
            is_active = self.redis_client.sismember("active_tasks", task_id)

            # 检查结果是否存在
            product_key = self.TASK_PRODUCTS_PREFIX.format(task_id=task_id)
            package_key = self.TASK_PACKAGES_PREFIX.format(task_id=task_id)

            product_exists = self.redis_client.exists(product_key)
            package_exists = self.redis_client.exists(package_key)

            # 获取结果数量
            product_count = 0
            package_count = 0

            if product_exists:
                count_str = self.redis_client.get(f"{product_key}:count")
                product_count = int(count_str) if count_str else 0

            if package_exists:
                count_str = self.redis_client.get(f"{package_key}:count")
                package_count = int(count_str) if count_str else 0

            # 判断状态
            if is_active:
                status = "running"
            elif product_exists or package_exists:
                status = "completed"
            else:
                status = "unknown"

            return {
                "task_id": task_id,
                "status": status,
                "is_active": bool(is_active),
                "product_count": product_count,
                "package_count": package_count,
                "total_count": product_count + package_count,
            }

        except redis.ConnectionError as e:
            logger.error(f"Redis connection error: {e}")
            return {
                "task_id": task_id,
                "status": "error",
                "error": "Redis connection failed",
            }
        except Exception as e:
            logger.error(f"Error checking task status in Redis: {e}")
            return {
                "task_id": task_id,
                "status": "error",
                "error": str(e),
            }

    async def check_redis_health(self) -> dict[str, Any]:
        """检查 Redis 连接健康状态"""
        try:
            self.redis_client.ping()
            info = self.redis_client.info()
            return {
                "status": "ok",
                "connected": True,
                "redis_version": info.get("redis_version"),
                "used_memory_human": info.get("used_memory_human"),
            }
        except redis.ConnectionError as e:
            return {"status": "error", "connected": False, "error": str(e)}
        except Exception as e:
            return {"status": "error", "connected": False, "error": str(e)}

    async def schedule_spider(
        self, project: str, spider: str, **kwargs: Any
    ) -> ScrapydScheduleResponse:
        """
        调度爬虫任务（包装父类方法，自动处理 task_id）

        Args:
            project: 项目名称
            spider: 爬虫名称
            **kwargs: 传递给爬虫的参数

        Returns:
            ScrapydScheduleResponse: 调度结果
        """
        return await self.schedule(project, spider, **kwargs)

    # 别名方法，方便调用
    daemon_status = AsyncScrapydClient.daemon_status
    schedule = AsyncScrapydClient.schedule
    cancel = AsyncScrapydClient.cancel
    list_projects = AsyncScrapydClient.list_projects
    list_versions = AsyncScrapydClient.list_versions
    list_spiders = AsyncScrapydClient.list_spiders
    list_jobs = AsyncScrapydClient.list_jobs
    delete_version = AsyncScrapydClient.delete_version
    delete_project = AsyncScrapydClient.delete_project
    get_log = AsyncScrapydClient.get_log
    get_items = AsyncScrapydClient.get_items
