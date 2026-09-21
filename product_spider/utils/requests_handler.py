"""基于 requests 库的 Scrapy 下载器

用于绕过雷池(SafeLine) WAF 的 TLS 指纹检测：
scrapy 默认下载器(Twisted)和 curl 一律 403，requests(urllib3) 指纹放行。

cookie 由 Scrapy 的 CookiesMiddleware 在请求/响应头层面维护，
本 handler 只需透传请求头并带回响应头即可。
"""
import requests
from scrapy.http import HtmlResponse
from twisted.internet import threads


class RequestsDownloadHandler:

    def __init__(self, settings):
        self.timeout = settings.getfloat('DOWNLOAD_TIMEOUT', 180)

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)

    def download_request(self, request, spider):
        return threads.deferToThread(self._download, request)

    def _download(self, request):
        headers = {k.decode(): b','.join(v).decode() for k, v in request.headers.items()}
        # 让 requests 自行处理压缩，避免与 HttpCompressionMiddleware 重复解压
        headers.pop('Accept-Encoding', None)
        r = requests.request(request.method, request.url, data=request.body or None,
                             headers=headers, timeout=self.timeout, allow_redirects=False)
        resp_headers = [(k.encode(), [v.encode()]) for k, v in r.headers.items()
                        if k.lower() not in ('content-encoding', 'content-length', 'transfer-encoding', 'connection')]
        return HtmlResponse(request.url, status=r.status_code, headers=resp_headers,
                            body=r.content, request=request, encoding='utf-8')

    def close(self):
        pass
