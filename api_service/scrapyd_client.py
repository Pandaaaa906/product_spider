"""
ScrapydClient - 带 Redis 结果获取功能的 Scrapyd 客户端

继承自 AsyncScrapydClient，添加从 Redis 获取爬虫任务结果的功能
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError

from api_service.async_scrapyd_client import AsyncScrapydClient
from api_service.schemas import (
    Product,
    ProductPackage,
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
        self._redis_client: Redis | None = None

    @property
    def redis_client(self) -> Redis:
        """获取 Redis 客户端（延迟初始化）"""
        if self._redis_client is None:
            self._redis_client = Redis.from_url(
                self.redis_url, decode_responses=True
            )
        return self._redis_client

    async def close(self) -> None:
        """关闭客户端连接"""
        await super().close()
        if self._redis_client is not None:
            await self._redis_client.close()
            self._redis_client = None

    async def get_task_results_from_redis(
        self,
        task_id: str,
    ) -> dict[str, Any]:
        """
        从 Redis 获取任务结果（同时获取 product 和 package，按 cat_no 关联）

        Args:
            task_id: 任务 ID

        Returns:
            包含 Product 列表（含关联的 packages）的字典
        """
        try:
            # 构建 Redis keys
            product_key = self.TASK_PRODUCTS_PREFIX.format(task_id=task_id)
            package_key = self.TASK_PACKAGES_PREFIX.format(task_id=task_id)
            product_count_key = f"{product_key}:count"

            logger.debug(f"Fetching results from Redis: {product_key}, {package_key}")

            # 获取 product 总数
            total_str = await self.redis_client.get(product_count_key)
            total = int(total_str) if total_str else 0

            # 获取 products 列表
            products_data = await self.redis_client.zrange(
                product_key, 0, -1, withscores=False
            )

            # 获取所有 packages（用于关联）
            packages_data = await self.redis_client.zrange(
                package_key, 0, -1, withscores=False
            )

            # 解析 packages 并按 (brand, cat_no) 分组
            packages_by_key: dict[tuple[str, str], list[dict]] = {}
            for item in packages_data:
                try:
                    pkg = json.loads(item) if isinstance(item, str) else json.loads(item.decode("utf-8"))
                    cat_no = pkg.get("cat_no") or pkg.get("cat_no_unit")
                    brand = pkg.get("brand", "")
                    if cat_no:
                        key = (brand, cat_no)
                        if key not in packages_by_key:
                            packages_by_key[key] = []
                        packages_by_key[key].append(pkg)
                except (json.JSONDecodeError, AttributeError) as e:
                    logger.warning(f"Failed to parse package item: {e}")
                    continue

            # 解析 products 并关联 packages
            products: list[Product] = []
            for item in products_data:
                try:
                    prod_dict = json.loads(item) if isinstance(item, str) else json.loads(item.decode("utf-8"))
                    cat_no = prod_dict.get("cat_no")
                    brand = prod_dict.get("brand", "")

                    # 获取关联的 packages（必须同时匹配 brand 和 cat_no）
                    related_packages = []
                    if cat_no:
                        key = (brand, cat_no)
                        if key in packages_by_key:
                            for pkg_dict in packages_by_key[key]:
                                related_packages.append(ProductPackage(**pkg_dict))

                    # 创建 Product 对象
                    product = Product(
                        **{k: v for k, v in prod_dict.items() if k != "packages"},
                        packages=related_packages,
                    )
                    products.append(product)

                except (json.JSONDecodeError, AttributeError) as e:
                    logger.warning(f"Failed to parse product item: {e}")
                    continue

            return {
                "task_id": task_id,
                "results": products,
                "total": total,
            }

        except RedisConnectionError as e:
            logger.error(f"Redis connection error: {e}")
            return {
                "task_id": task_id,
                "results": [],
                "total": 0,
                "error": "Redis connection failed",
            }
        except Exception as e:
            logger.error(f"Error fetching results from Redis: {e}")
            return {
                "task_id": task_id,
                "results": [],
                "total": 0,
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
            is_active = await self.redis_client.sismember("active_tasks", task_id)

            # 检查结果是否存在
            product_key = self.TASK_PRODUCTS_PREFIX.format(task_id=task_id)
            package_key = self.TASK_PACKAGES_PREFIX.format(task_id=task_id)

            product_exists = await self.redis_client.exists(product_key)
            package_exists = await self.redis_client.exists(package_key)

            # 获取结果数量
            product_count = 0
            package_count = 0

            if product_exists:
                count_str = await self.redis_client.get(f"{product_key}:count")
                product_count = int(count_str) if count_str else 0

            if package_exists:
                count_str = await self.redis_client.get(f"{package_key}:count")
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

        except RedisConnectionError as e:
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
            await self.redis_client.ping()
            info = await self.redis_client.info()
            return {
                "status": "ok",
                "connected": True,
                "redis_version": info.get("redis_version"),
                "used_memory_human": info.get("used_memory_human"),
            }
        except RedisConnectionError as e:
            return {"status": "error", "connected": False, "error": str(e)}
        except Exception as e:
            return {"status": "error", "connected": False, "error": str(e)}

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
