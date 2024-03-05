import logging
from typing import Optional, Callable

import requests
from scrapy import Request
from scrapy.exceptions import NotConfigured

from product_spider import signals as ps_signals

logger = logging.getLogger("scrapy.proxies")
DEFAULT_PROXY_POOL_REFRESH_STATUS_CODES = {503, 403}


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
        self.refresh_status_codes = settings.get(
            "PROXY_POOL_REFRESH_STATUS_CODES", DEFAULT_PROXY_POOL_REFRESH_STATUS_CODES
        )
        if not proxy_url:
            raise NotConfigured
        self.PROXY_POOL_URL = proxy_url
        self.refresh_proxy()
        if f := getattr(spider, 'is_proxy_invalid', self.default_is_proxy_invalid):
            self.is_proxy_invalid = f

    @classmethod
    def from_crawler(cls, crawler):
        mid = cls(crawler.settings, spider=crawler.spider)
        crawler.signals.connect(mid.refresh_proxy, signal=ps_signals.SHOULD_REFRESH_PROXY)
        return mid

    def refresh_proxy(self, proxy: str = None):
        logger.info(f"current proxy: {self.proxy}")
        if not proxy or not proxy.startswith('http'):
            proxy = get_proxy(proxy_url=self.PROXY_POOL_URL)
        self.proxy = proxy
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

    def default_is_proxy_invalid(self, request, response):
        proxy = request.meta.get('proxy')
        if response.status in self.refresh_status_codes:
            logger.warning(f'status code:{response.status}, {request.url}, using proxy {proxy}')
            return True
        return False

