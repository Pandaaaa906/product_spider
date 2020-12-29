import re
from urllib.parse import urljoin

from more_itertools import first
from scrapy import Request

from product_spider.items import RawData, ProductPackage
from product_spider.utils.functions import strip
from product_spider.utils.spider_mixin import BaseSpider


class USPSpider(BaseSpider):
    name = "usp"
    brand = 'USP'
    start_urls = ["https://store.usp.org/OA_HTML/ibeCCtpSctDspRte.jsp?section=10042", ]
    base_url = "https://store.usp.org/"

    def parse(self, response):
        rel_urls = response.xpath('//div[@id="alphabrowsekey"]//a/@href').getall()
        for rel_url in rel_urls:
            yield Request(urljoin(response.url, rel_url), callback=self.parse_list)

    def parse_list(self, response):
        rel_urls = response.xpath('//table[@class="OraBGAccentDark"]//tr[position()>1]/td[2]/a/@href').getall()
        for rel_url in rel_urls:
            yield Request(urljoin(response.url, rel_url), callback=self.parse_detail)

    def parse_detail(self, response):
        tmp = '//td[contains(text(), {!r})]/following-sibling::td/text()'
        cat_no = response.xpath(tmp.format('Catalog #')).get()
        d = {
            'brand': self.brand,
            'cat_no': cat_no,
            'en_name': response.xpath('//td[@class="pageTitle"]/text()').get(),
            'cas': response.xpath(tmp.format('CAS#')).get(),
            'stock_info': response.xpath(tmp.format('In Stock')).get(),
            'prd_url': response.url,
        }
        yield RawData(**d)

        raw_price = strip(response.xpath(
            'normalize-space(//td[contains(text(), "Retail Price:")]/following-sibling::td/text())'
        ).get())
        price = None
        if raw_price:
            raw_price = re.sub(r'\s+', ' ', raw_price)
            price = first(re.findall(r'(\d+(\.\d+)?)', raw_price), None)
        dd = {
            'brand': self.brand,
            'cat_no': cat_no,
            'price': price,
            'currency': 'USD',
            'info': raw_price,
            'delivery_time': response.xpath(tmp.format('In Stock')).get(),
        }
        yield ProductPackage(**dd)
