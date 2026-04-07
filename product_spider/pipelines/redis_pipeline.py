import time

import redis
import orjson

from scrapy import signals

from product_spider.items import ProductPackage, RawData


class KeywordSearchRedisPipeline:
    """Redis Pipeline for storing search results"""

    # 默认缓存过期时间：24小时（秒）
    DEFAULT_CACHE_TTL = 86400
    KEY_PREFIX = "CMD_KEYWORD_SEARCH"

    def __init__(self, redis_url: str, cache_ttl: int = None):
        self.redis_url = redis_url
        self.redis = None
        self.cache_ttl = cache_ttl or self.DEFAULT_CACHE_TTL
        self.spider_closed_reason = {}
        self._closed = False

    @classmethod
    def from_crawler(cls, crawler):
        redis_url = crawler.settings.get('REDIS_URL')
        if not redis_url:
            raise ValueError("REDIS_URL not configured in settings")
        # 从 settings 获取缓存过期时间，默认 24 小时
        cache_ttl = crawler.settings.getint('REDIS_CACHE_TTL', cls.DEFAULT_CACHE_TTL)
        s = cls(redis_url, cache_ttl)
        crawler.signals.connect(s.on_spider_open, signal=signals.spider_opened)
        crawler.signals.connect(s.on_spider_close, signal=signals.spider_closed)
        return s

    def open_spider(self, spider):
        """Initialize connection to Redis"""
        self.redis = redis.from_url(self.redis_url, decode_responses=True)
        spider.logger.info(f"Connected to Redis: {self.redis_url}")

    def close_spider(self, spider, reason=None):
        """Close Redis connection"""
        self._closed = True

    @staticmethod
    def _is_spider_keyword_search(spider):
        return hasattr(spider, 'task_id') and spider.task_id

    def process_item(self, item, spider):
        """Process each item and store it to Redis"""
        # 如果没有task_id跳过
        if not self._is_spider_keyword_search(spider):
            return item
        if not isinstance(item, (ProductPackage, RawData)):
            return item
        # 如果是搜索请求且有task_id，存储到Redis
        try:
            task_id = spider.task_id
            item_dict = dict(item)

            # 存储结果到Sorted Set（按时间排序）
            item_json = orjson.dumps(item_dict)
            if isinstance(item, RawData):
                key = f"{self.KEY_PREFIX}:{task_id}:results:product"
            elif isinstance(item, ProductPackage):
                key = f"{self.KEY_PREFIX}:{task_id}:results:package"
            self.redis.zadd(key, {item_json: time.time()})

            # 记录第一个结果的到达时间
            if not self.redis.exists(f"{self.KEY_PREFIX}:{task_id}:first_result"):
                self.redis.set(f"{self.KEY_PREFIX}:{task_id}:first_result", time.time())
            else:
                self.redis.set(f"{self.KEY_PREFIX}:{task_id}:last_result", time.time())

            # 设置结果过期时间（默认24小时，可通过环境变量配置）
            self.redis.expire(key, self.cache_ttl)
            self.redis.expire(f"{self.KEY_PREFIX}:{task_id}:first_result", self.cache_ttl)
            self.redis.expire(f"{self.KEY_PREFIX}:{task_id}:last_result", self.cache_ttl)

            spider.logger.info(f"Stored item to Redis: task_id={task_id}, item={item.get('cat_no', 'N/A')}")

        except Exception as e:
            spider.logger.error(f"Error storing item to Redis: {e}")
        return item

    def _mark_task_completed(self, spider, reason: str):
        if not self._is_spider_keyword_search(spider):
            return
        """标记任务完成"""
        task_id = spider.task_id
        # 从活跃任务移除
        self.redis.srem("active_tasks", task_id)

        # 添加到完成列表（按完成时间排序）
        completion_time = time.time()
        self.redis.zadd("completed_tasks", {task_id: completion_time})

        # 设置过期时间
        self.redis.expire(f"{self.KEY_PREFIX}:{task_id}:status", self.DEFAULT_CACHE_TTL)  # 7天

        # 更新状态
        self.redis.set(f"{self.KEY_PREFIX}:{task_id}:status", reason)
        self.redis.set(f"{self.KEY_PREFIX}:{task_id}:completed_at", completion_time)

    def on_spider_open(self, spider):
        """

        :param spider:
        :return:
        """
        if not self._is_spider_keyword_search(spider):
            return
        self.redis.set(f"{self.KEY_PREFIX}:{spider.task_id}:status", "running")

    def on_spider_close(self, spider, reason=None):
        spider.logger.info(f'Spider ended: {spider.name}, {reason}')
        self._mark_task_completed(spider, reason)

        if self._closed and self.redis:
            self.redis.close()
