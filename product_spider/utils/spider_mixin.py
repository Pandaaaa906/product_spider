import json
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

    def __init__(self, cmd_keyword_search: bool = False, keyword: str = None, search_params: dict = None,
                 task_id: str = None, **kwargs):
        """

        :param cmd_keyword_search: 是否调用关键字搜索功能，keyword_search
        :param keyword: 关键字
        :param search_params: 高级搜索配置
        :param task_id: 任务ID
        :param kwargs:
        """
        self.cmd_keyword_search = True if cmd_keyword_search in {True, 'True', 'true', '1'} else False
        self.keyword = keyword

        # 处理 search_params - 如果是 JSON 字符串则解析为 dict
        if isinstance(search_params, str):
            try:
                search_params = json.loads(search_params)
            except json.JSONDecodeError:
                search_params = None
        self.search_params = search_params

        self.task_id = task_id
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
        if not self.task_id:
            raise ValueError("task_id is required when cmd_keyword_search is True")
        self.log(f"调用keyword_search, {self.keyword=}, {self.search_params=}")
        yield from self.keyword_search(self.keyword, self.search_params)

    def keyword_search(self, keyword: str, search_params: dict = None) -> Generator:
        """
        各个爬虫分别根据具体网站，实现关键词搜索功能，最终应该调用原本的parse_detail(detail_parse) 去yield Item(...)
        :param keyword: 搜索关键词
        :param search_params: 高级搜索参数，仅部分网站支持高级搜索时使用
        :return:
        """
        raise NotImplementedError

class JsonSpider(scrapy.Spider):
    headers = {
        'Content-Type': 'application/json',
        'accept': 'application/json, text/plain, */*',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
    }
