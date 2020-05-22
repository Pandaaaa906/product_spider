from string import ascii_uppercase
from urllib.parse import urljoin

from scrapy import Request
from scrapy.http import Response

from product_spider.items import RawData
from product_spider.utils.spider_mixin import BaseSpider


def get_value(response: Response, label: str):
    ret = response.xpath(f'//li[contains(text(), {label!r})]/text()').get('')
    ret = ret.replace(label, '').strip()
    return ret or None


class AllmpusSpider(BaseSpider):
    name = "allmpus"
    allowed_domains = ["allmpus.com"]
    base_url = "https://www.allmpus.com"
    start_urls = [
        f"https://www.allmpus.com/-{a}" for a in ascii_uppercase
    ]

    def parse(self, response):
        nodes = response.xpath('//div[@class="container"]/div/a')
        for node in nodes:
            rel_url = node.xpath('./@href').get()
            parent = node.xpath('.//b/text()').get('').strip() or None
            yield Request(
                urljoin(self.base_url, rel_url),
                callback=self.parse_prd_list,
                meta={'parent': parent}
            )

    def parse_prd_list(self, response):
        rel_urls = response.xpath('//div[@class="panel-body"]/a/@href').extract()
        for rel_url in rel_urls:
            yield Request(
                urljoin(self.base_url, rel_url),
                callback=self.parse_detail,
                meta=response.meta,
            )

    def parse_detail(self, response):
        img_rel_url = response.xpath('//div[@class="panel-body"]//div/img/@src').get()
        img_url = img_rel_url and urljoin(self.base_url, img_rel_url)
        d = {
            'brand': 'Allmpus',
            'parent': response.meta.get('parent', None),
            'cat_no': get_value(response, "CAT No : "),
            'en_name': response.xpath('//h1/text()').get(),
            'cas': get_value(response, "CAS Number : "),
            'mf': get_value(response, "Molecular Formula : "),
            'mw': get_value(response, "Molecular Weight : "),
            'stock_info': get_value(response, "Inventory Status :"),
            'purity': get_value(response, "Purity by HPLC :"),
            'img_url': img_url,
            'info1': get_value(response, "Chemical Name :"),
            'info2': get_value(response, "Storage :"),
            'prd_url': response.url,
        }
        yield RawData(**d)
