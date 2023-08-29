import json
from os import getenv
from time import time

from scrapy import FormRequest

from items.soopat import SooPATPatent
from product_spider.utils.spider_mixin import BaseSpider


class SooPATSpider(BaseSpider):
    name = "soopat"
    start_urls = ['http://vip.soopat.com/Account/Login']
    url_login = "http://vip.soopat.com/Account/ajaxLoginPost"
    url_search = "http://vip.soopat.com/World/ajaxResult"

    def __init__(self, keyword: str = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.keyword = keyword or "Photoelectric material"

    def start_requests(self):
        username = getenv("SOOPAT_USER")
        password = getenv("SOOPAT_PWD")
        yield FormRequest(
            self.url_login,
            method="POST",
            formdata={
                "TokenId": "",
                "Rnd": f"{time():.0f}",
                "RndResult": "",
                "Account": username,
                "Password": password
            },
            callback=self.parse
        )

    def make_search_request(self, keyword: str, page: int = 1, per_page: int = 30, meta=None, **kwargs):
        if meta is None:
            meta = {}
        d = {
            "terms": [], "PageSize": per_page, "FMZL": "Y", "SYXX": "Y", "WGZL": "Y", "FMSQ": "Y", "Countrys": "",
            "lsCountrys": [], "Dist": None, "Sort": None, "SearchType": 1, "SearchId": None, "SearchIdPT": None,
            "Valid": None, "FAMCT": None, "ALL": "", "MC": "", "ZY": "", "ZQX": None, "SMS": "", "QLYQ": None,
            "SQH": None, "GKH": None, "DZ": "", "ZLDLJG": "", "DLR": "", "YXQ": None, "GJGB": None, "GJSQ": None,
            "JRGJRQ": None, "BZRQ": None, "SQR": "", "FMR": "", "FLH": "", "GKRQFrom": "", "GKRQTo": "", "SQRQFrom": "",
            "SQRQTo": "", "RefineIsNot": "", "MCZYZQX": None, "MCZYQLYQ": "",
            "MainQueryString": keyword, "FolderIds": None, "Page": page}
        return FormRequest(
            self.url_search,
            method="POST",
            formdata={"SW": json.dumps(d)},
            meta={"keyword": keyword, **meta},
            **kwargs
        )

    def parse(self, response, **kwargs):
        yield self.make_search_request(self.keyword, callback=self.parse_list)

    def parse_list(self, response):
        j = json.loads(response.text)
        for record in j.get('Data', []):
            code = record.get('PN', '')
            d = {
                "code": code,
                "raw_json": json.dumps(record, ensure_ascii=False)
            }
            yield SooPATPatent(**d)
        pass
        keyword = response.meta.get("keyword", "")
        page = j.get('Page', 1)
        per_page = j.get('PageSize', 30)
        total = j.get('TotalCount', 0)
        if page * per_page < total:
            yield self.make_search_request(keyword, page=page + 1, per_page=per_page, callback=self.parse_list)
