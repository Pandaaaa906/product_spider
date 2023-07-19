import re
from urllib.parse import urljoin

from more_itertools import first
from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider


class ChangKuanTechSpider(BaseSpider):
    name = "changkuantech"
    start_urls = ["http://www.changkuantech.com/product.html"]

    def parse(self, response, **kwargs):
        rel_urls = response.xpath('//span/a/@href').getall()
        for rel_url in rel_urls:
            yield Request(
                url=urljoin(response.url, rel_url),
                callback=self.parse_detail
            )
        next_page = response.xpath('//span[@class="current"]/following-sibling::a/@href').get()
        if next_page:
            yield Request(
                url=urljoin(response.url, next_page),
                callback=self.parse
            )

    @staticmethod
    def _extract_value(arr_str, pattern):
        m = first(filter(lambda x: x, (re.search(rf'{pattern}[:：]\s*(?P<value>.+)', t) for t in arr_str)), None)
        if not m:
            return
        return m.group(1)

    def parse_detail(self, response):
        _id = (m := re.search(r'/id/(\d+)\.html', response.url)) and m.group(1)
        rel_img = response.xpath('//div[@class="div2"]//img/@src').get()
        text = response.xpath('//div[@class="div2"]//p/text()').getall()
        d = {
            "brand": self.name,
            "cat_no": f"{str.upper(self.name)}-{_id}",
            "chs_name": strip(response.xpath('//div[@class="div3"]/text()').get()),
            "en_name": self._extract_value(text, '名称'),
            "cas": self._extract_value(text, 'CAS'),
            "purity": self._extract_value(text, '纯度'),
            "appearance": self._extract_value(text, '外观'),
            "prd_url": response.url,
            "img_url": rel_img and urljoin(response.url, rel_img),
        }
        yield RawData(**d)
