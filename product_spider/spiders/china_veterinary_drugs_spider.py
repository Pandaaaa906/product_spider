import json
from functools import partial

from scrapy.http import JsonRequest

from product_spider.items import CVDRegData, CVDClinicalData, CVDBioInspectData, CVDApprovedRegData
from product_spider.utils.spider_mixin import BaseSpider


class ChinaVeDrugSpider(BaseSpider):
    name = 'china_ve_drug'
    start_urls = [
        "http://124.126.15.169:8081/cx/"
    ]
    urls = (
        ("http://124.126.15.169:8081/cx/api/cxsj/gnxsyzc/list", CVDRegData),
        ("http://124.126.15.169:8081/cx/api/cxsj/lcsysp/list", CVDClinicalData),
        ("http://124.126.15.169:8081/cx/api/cxsj/syjdcjjg/list", CVDBioInspectData),
        ("http://124.126.15.169:8081/cx/api/cxsj/sycppzwh/list", CVDApprovedRegData),
    )

    def parse(self, response, **kwargs):
        for url, item_type in self.urls:
            yield self.make_request(url, item_type)

    def make_request(self, url, item_type: dict, page: int = 1, rows: int = 50, conditions: list = ()):
        d = {
            "page": page,
            "rows": rows,
            "conditionItems": conditions
        }
        return JsonRequest(
            url=url,
            data=d,
            method="POST",
            callback=partial(self._parse_data, item_type=item_type),
            meta={"data": d}
        )

    def _parse_data(self, response, item_type):
        data = response.meta.get("data")
        j = json.loads(response.text)
        for row in (rows := j.get('rows', [])):
            yield item_type(**row)
        if not rows:
            return
        page = data.get('page', 0)
        rows = data.get('rows', 0)
        yield self.make_request(response.url, item_type, page=page + 1, rows=rows)
