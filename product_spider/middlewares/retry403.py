import logging

from twisted.internet import reactor
from twisted.internet.task import deferLater

logger = logging.getLogger(__name__)


class BackoffRetry403Middleware:
    """403 递增间隔重试：第 n 次重试前等待 n * retry_403_delay 秒。

    在 spider 的 custom_settings 中注册启用，可通过 spider 属性调整：
    max_403_retries（默认 5）、retry_403_delay（默认 10 秒）。
    重试期间请求挂在 downloader 的 transferring 队列中，spider 不会因空闲被关闭。
    """

    def process_response(self, request, response, spider):
        if response.status != 403:
            return response
        max_retries = getattr(spider, 'max_403_retries', 5)
        base_delay = getattr(spider, 'retry_403_delay', 10)
        n = request.meta.get('retry_403_times', 0)
        if n >= max_retries:
            logger.error(f"403, give up after {n} retries: {request.url}")
            return response
        delay = (n + 1) * base_delay
        logger.warning(f"403 {request.url}, retry {n + 1}/{max_retries} after {delay}s")
        new_request = request.replace(dont_filter=True)
        new_request.meta['retry_403_times'] = n + 1
        return deferLater(reactor, delay, lambda: new_request)
