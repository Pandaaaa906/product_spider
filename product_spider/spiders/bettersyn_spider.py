from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData
from product_spider.utils.spider_mixin import BaseSpider


class BetterSynSpider(BaseSpider):
    name = "bettersyn"
    allowd_domains = ["bettersyn.com"]
    start_urls = [
        "http://www.bettersyn.com/list-13-1.html",
        "http://www.bettersyn.com/list-14-1.html",
    ]
    base_url = "http://www.bettersyn.com/"

    def parse(self, response):
        rel_urls = response.xpath('//div[@class="x_abnewsbpic"]/a/@href').getall()
        for rel_url in rel_urls:
            yield Request(url=urljoin(self.base_url, rel_url), callback=self.parse_detail)

        next_page = response.xpath('//div[@class="page"]//span/following-sibling::a[not(@class)]/@href').get()
        if next_page:
            yield Request(url=urljoin(self.base_url, next_page), callback=self.parse)

    def parse_detail(self, response):
        tmp = '//span[contains(text(), {!r})]/span/text()'
        *_, en_name = response.xpath('normalize-space(//span[contains(text(), "Product name")]/text())')\
            .get('').split(': ')
        d = {
            'brand': 'BetterSyn',
            'cat_no': response.xpath(tmp.format('CAS NO')).get(),
            'en_name': en_name,
            'info1': en_name,
            'cas': response.xpath(tmp.format('CAS NO')).get(),
            'img': response.xpath('//div/img/@src').get(),
            'prd_url': response.url,
        }
        yield RawData(**d)
