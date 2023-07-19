import re
from urllib.parse import urljoin

from more_itertools import first
from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider


class HaiKuoChemSpider(BaseSpider):
    name = "haikuochem"
    start_urls = ["http://www.haikuochem.com/products.asp"]

    def parse(self, response, **kwargs):
        rel_urls = response.xpath('//div[@id="other_products"]//td/a/@href').getall()
        for rel_url in rel_urls:
            yield Request(
                url=urljoin(response.url, rel_url),
                callback=self.parse_detail
            )
        next_page = response.xpath('//a[text()="[下一页]"]/@href').get()
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
        text = ('\r\n'.join((''.join(p.xpath('.//text()').getall()) for p in response.xpath('//td/p'))).split('\r\n'))
        text = tuple(filter(lambda x: x, map(lambda x: x.strip().replace('\xa0', ' '), text)))
        img_url = response.xpath('//div[@id="imgView"]//img/@src').get()
        cas = self._extract_value(text, "CAS NO.")
        chs_name = strip(response.xpath('//h1/text()').get())
        if not cas:
            cas = (m := re.search(r'\d+-\d+-\d', chs_name)) and m.group(0)
        _id = (m := re.search(r'id=(\d+)', response.url)) and m.group(1)
        d = {
            "brand": self.name,
            "parent": response.xpath('//div[@id="mbx_nav"]/a[last()]/text()').get(),
            "cat_no": f"{str.upper(self.name)}-{_id}",
            "chs_name": chs_name,
            "en_name": self._extract_value(text, "英文名"),
            "cas": cas,
            "purity": self._extract_value(text, "含量"),
            "img_url": img_url and urljoin(response.url, img_url),
            "prd_url": response.url,
        }
        yield RawData(**d)
