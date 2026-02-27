from typing import Generator

import scrapy


class BaseSpider(scrapy.Spider):
    """
    爬虫基类
    继承了这个类，如果传入cmd_keyword_search=True，提供keyword 或者search_params, 并且重载了keyword_search方法
    会调用keyword_search开始爬虫
    尽量不要重载`start_requests`，而是重载 `_start_requests`
    """
    headers = {
        "accept-encoding": "gzip, deflate, sdch, br",
        "accept-language": "zh-CN,zh;q=0.8",
        "upgrade-insecure-requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
    }

    _start_requests: Generator = None

    def __init__(self, cmd_keyword_search: bool = False, keyword: str = None, search_params: dict = None, **kwargs):
        self.cmd_keyword_search = cmd_keyword_search
        self.keyword = keyword
        self.search_params = search_params
        super().__init__(**kwargs)

    def start_requests(self):
        if not self.cmd_keyword_search:
            if self._start_requests is not None:
                yield from self._start_requests()
            else:
                yield from super().start_requests()
            return
        if not self.keyword and not self.search_params:
            raise ValueError("keyword or search_params not specified")
        yield from self.keyword_search(self.keyword, self.search_params)

    def keyword_search(self, keyword: str, search_params: dict) -> Generator:
        raise NotImplementedError

class JsonSpider(scrapy.Spider):
    headers = {
        'Content-Type': 'application/json',
        'accept': 'application/json, text/plain, */*',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
    }
