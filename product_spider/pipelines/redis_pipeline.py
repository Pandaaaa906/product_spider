import json
import time

import redis
from scrapy.exceptions import DropItem


class RedisPipeline:
    """Redis Pipeline for storing search results"""

    # 默认缓存过期时间：24小时（秒）
    DEFAULT_CACHE_TTL = 86400

    def __init__(self, redis_url: str, cache_ttl: int = None):
        self.redis_url = redis_url
        self.redis = None
        self.cache_ttl = cache_ttl or self.DEFAULT_CACHE_TTL

    @classmethod
    def from_crawler(cls, crawler):
        redis_url = crawler.settings.get('REDIS_URL')
        if not redis_url:
            raise ValueError("REDIS_URL not configured in settings")
        # 从 settings 获取缓存过期时间，默认 24 小时
        cache_ttl = crawler.settings.getint('REDIS_CACHE_TTL', cls.DEFAULT_CACHE_TTL)
        return cls(redis_url, cache_ttl)

    def open_spider(self, spider):
        """Initialize connection to Redis"""
        self.redis = redis.from_url(self.redis_url, decode_responses=True)
        spider.logger.info(f"Connected to Redis: {self.redis_url}")

    def close_spider(self, spider):
        """Close Redis connection"""
        if self.redis:
            self.redis.close()

    def process_item(self, item, spider):
        """Process each item and store it to Redis"""
        try:
            # 如果是搜索请求且有task_id，存储到Redis
            if hasattr(spider, 'task_id') and spider.task_id:
                task_id = spider.task_id
                item_dict = dict(item)

                # 存储结果到Sorted Set（按时间排序）
                item_json = json.dumps(item_dict, ensure_ascii=False)
                self.redis.zadd(f"task:{task_id}:results",
                              {item_json: time.time()})

                # 更新计数
                self.redis.incr(f"task:{task_id}:results:count")

                # 添加到任务索引
                self.redis.sadd("active_tasks", task_id)

                # 记录第一个结果的到达时间
                if not self.redis.exists(f"task:{task_id}:first_result"):
                    self.redis.set(f"task:{task_id}:first_result", time.time())

                # 设置结果过期时间（默认24小时，可通过环境变量配置）
                self.redis.expire(f"task:{task_id}:results", self.cache_ttl)
                self.redis.expire(f"task:{task_id}:results:count", self.cache_ttl)
                self.redis.expire(f"task:{task_id}:first_result", self.cache_ttl)
                self.redis.expire(f"task:{task_id}:last_result", self.cache_ttl)

                spider.logger.info(f"Stored item to Redis: task_id={task_id}, item={item.get('cat_no', 'N/A')}")

            return item

        except Exception as e:
            spider.logger.error(f"Error storing item to Redis: {e}")
            raise DropItem(f"Redis pipeline error: {e}")

    @staticmethod
    def get_task_results(redis_client, task_id: str, limit: int = 100, offset: int = 0):
        """获取任务结果"""
        # 获取结果总数
        total = redis_client.zcard(f"task:{task_id}:results")

        # 获取分页结果
        start = offset
        end = offset + limit - 1

        if end >= total:
            end = total - 1

        results = redis_client.zrange(f"task:{task_id}:results", start, end, withscores=True)

        # 解析结果
        parsed_results = []
        for item_json, score in results:
            item = json.loads(item_json)
            parsed_results.append({
                'item': item,
                'timestamp': score,
                'score': score
            })

        return {
            'results': parsed_results,
            'total': total,
            'limit': limit,
            'offset': offset
        }

    @staticmethod
    def get_task_status(redis_client, task_id: str):
        """获取任务状态"""
        status = {
            'task_id': task_id,
            'status': 'completed',
            'total_items': redis_client.get(f"task:{task_id}:results:count") or 0,
            'first_result': redis_client.get(f"task:{task_id}:first_result"),
            'last_result': redis_client.get(f"task:{task_id}:last_result"),
            'created_at': redis_client.get(f"task:{task_id}:created_at"),
            'spider': redis_client.get(f"task:{task_id}:spider"),
            'keyword': redis_client.get(f"task:{task_id}:keyword"),
        }
        return status

    @staticmethod
    def mark_task_completed(redis_client, task_id: str):
        """标记任务完成"""
        # 从活跃任务移除
        redis_client.srem("active_tasks", task_id)

        # 添加到完成列表（按完成时间排序）
        completion_time = time.time()
        redis_client.zadd("completed_tasks", {task_id: completion_time})

        # 设置过期时间
        redis_client.expire(f"task:{task_id}:status", 604800)  # 7天

        # 更新状态
        redis_client.set(f"task:{task_id}:status", "completed")
        redis_client.set(f"task:{task_id}:completed_at", completion_time)