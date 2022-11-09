import logging

import requests
from scrapy.exceptions import NotConfigured

log = logging.getLogger(__name__)


def get_proxy(proxy_url):
    r = requests.get(proxy_url)
    return f'http://{r.text}'


def wrap_failed_request(request):
    request.meta.update({'refresh_proxy': True})
    request.replace(dont_filter=True, priority=99999)
    return request


class RandomProxyMiddleWare:
    """代理中间件"""
    proxy = None
    PROXY_POOL_URL = None
    logger = None

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        proxy_url = crawler.settings.get("PROXY_POOL_URL")
        if not proxy_url:
            raise NotConfigured
        s.proxy = get_proxy(proxy_url=proxy_url)
        s.PROXY_POOL_URL = proxy_url
        return s

    def refresh_proxy(self):
        self.proxy = get_proxy(proxy_url=self.PROXY_POOL_URL)

    def process_request(self, request, spider):
        flag = request.meta.pop("refresh_proxy", False)
        if flag and self.proxy == request.meta.get("proxy"):
            log.info(f"current proxy: {self.proxy}")
            self.refresh_proxy()
            log.info(f"changed proxy to: {self.proxy}")
            request.cookies = {}
        request.meta["proxy"] = self.proxy
        return

    def process_exception(self, request, exception, spider):
        # TODO might need add some proxy retry marks
        if isinstance(exception, ConnectionRefusedError):
            self.refresh_proxy()
            return wrap_failed_request(request)
        return