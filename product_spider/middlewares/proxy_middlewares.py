import logging
from typing import Optional, Callable

import requests
from scrapy import Request
from scrapy.exceptions import NotConfigured
from twisted.internet.error import TCPTimedOutError

logger = logging.getLogger("scrapy.proxies")


def get_proxy(proxy_url):
    r = requests.get(proxy_url)
    return f'http://{r.text}'


def wrap_failed_request(request: Request):
    new_request = request.replace(dont_filter=True, priority=99999)
    return new_request


class RandomProxyMiddleWare:
    """代理中间件"""
    proxy: str = None
    PROXY_POOL_URL: str = None
    is_proxy_invalid: Optional[Callable] = None

    def __init__(self, settings, spider=None):
        proxy_url = settings.get("PROXY_POOL_URL")
        if not proxy_url:
            raise NotConfigured
        self.PROXY_POOL_URL = proxy_url
        self.refresh_proxy()
        if f := getattr(spider, 'is_proxy_invalid', self.default_is_proxy_invalid):
            self.is_proxy_invalid = f

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings, spider=crawler.spider)

    def refresh_proxy(self):
        logger.info(f"current proxy: {self.proxy}")
        self.proxy = get_proxy(proxy_url=self.PROXY_POOL_URL)
        logger.info(f"changed proxy to: {self.proxy}")

    def process_request(self, request, spider):
        if self.proxy != request.meta.get("proxy"):
            request.meta["proxy"] = self.proxy
            request.cookies = {}
        return

    def process_response(self, request, response, spider):
        if not self.is_proxy_invalid:
            return response
        if not self.is_proxy_invalid(request, response):
            return response
        if request.meta.get('proxy') == self.proxy:
            self.refresh_proxy()
        return wrap_failed_request(request)

    def process_exception(self, request, exception, spider):
        if request.meta.get('proxy') == self.proxy:
            self.refresh_proxy()
        logger.warning(f"{exception}: {request.url}")
        return wrap_failed_request(request)

    @staticmethod
    def default_is_proxy_invalid(request, response):
        proxy = request.meta.get('proxy')
        if response.status in {503, 403}:  # TODO dynamic settings
            logger.warning(f'status code:{response.status}, {request.url}, using proxy {proxy}')
            return True
        return False

