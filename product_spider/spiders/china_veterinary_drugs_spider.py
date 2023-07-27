import json

from scrapy.http import JsonRequest

from product_spider.items import CVDRegData, CVDClinicalData, CVDBioInspectData
from product_spider.utils.spider_mixin import BaseSpider


class ChinaVeDrugSpider(BaseSpider):
    name = 'china_ve_drug'
    start_urls = [
        "http://124.126.15.169:8081/cx/"
    ]
    urls = (
        ("http://124.126.15.169:8081/cx/api/cxsj/gnxsyzc/list", "parse_new_drug_data"),
        ("http://124.126.15.169:8081/cx/api/cxsj/lcsysp/list", "parse_clinical_data"),
        ("http://124.126.15.169:8081/cx/api/cxsj/syjdcjjg/list", "parse_bio_drug_inspect_data"),
    )

    def parse(self, response, **kwargs):
        for url, parser in self.urls:
            yield self.make_request(url, parser)

    def make_request(self, url, parser_name: str, page: int = 1, rows: int = 50, conditions: list = ()):
        d = {
            "page": page,
            "rows": rows,
            "conditionItems": conditions
        }
        return JsonRequest(
            url=url,
            data=d,
            method="POST",
            callback=getattr(self, parser_name),
            meta={"data": d, "parser_name": parser_name}
        )

    def _parse_data(self, response, item_type):
        data = response.meta.get("data")
        parser_name = response.meta.get("parser_name")
        j = json.loads(response.text)
        for row in (rows := j.get('rows', [])):
            yield item_type(**row)
        if not rows:
            return
        page = data.get('page', 0)
        rows = data.get('rows', 0)
        yield self.make_request(response.url, parser_name, page=page + 1, rows=rows)

    def parse_new_drug_data(self, response):
        yield from self._parse_data(response, CVDRegData)

    def parse_clinical_data(self, response):
        yield from self._parse_data(response, CVDClinicalData)

    def parse_bio_drug_inspect_data(self, response):
        yield from self._parse_data(response, CVDBioInspectData)
