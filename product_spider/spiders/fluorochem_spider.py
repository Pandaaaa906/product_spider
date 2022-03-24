import re
from urllib.parse import urljoin

from more_itertools import first
from scrapy import Request
from product_spider.utils.spider_mixin import BaseSpider
from product_spider.utils.functions import strip
from product_spider.items import RawData, ProductPackage


class FluorochemSpider(BaseSpider):
    name = "fluorochem"
    start_urls = ["http://www.fluorochem.co.uk/Products/Products", ]
    base_url = "http://www.fluorochem.co.uk/"
    brand = 'fluorochem'

    def parse(self, response, **kwargs):
        rows = response.xpath('//table[@id="tblSearchResults"]//tr[position()>1]')
        for row in rows:
            prd = {
                'cat_no': rows.xpath('./td[1]/text()').get(),
                'en_name': rows.xpath('./td[2]/text()').get(),
            }
            rel_url = row.xpath('.//a/@href').get()
            yield Request(urljoin(response.url, rel_url), callback=self.parse_detail, meta=prd)
        next_page = response.xpath('//div[@title="Next Page"]/parent::a/@href').get()
        if next_page:
            yield Request(urljoin(response.url, next_page), callback=self.parse)

    def parse_detail(self, response):
        tmp = '//th[contains(text(), {!r})]/following-sibling::td/text()'
        p = re.compile(r'(\d+(\.\d+)?)')
        d = {
            'brand': self.brand,
            'cat_no': response.meta.get('cat_no'),
            'en_name': response.meta.get('en_name'),
            'cas': strip(response.xpath(tmp.format("CAS Number")).get()),
            'mf': strip(response.xpath(tmp.format("Molecular Formula")).get()),
            'mw': strip(response.xpath(tmp.format("Molecular Weight")).get()),
            'purity': strip(response.xpath(tmp.format("Purity")).get()),
            'mdl': strip(response.xpath(tmp.format("MDL Number")).get()),

            'prd_url': response.url,
            'img_url': response.xpath('//div[@id="tabs-Structure"]/img/@src').get(),
        }
        yield RawData(**d)

        rows = response.xpath('//table[@id="tblPricing"]//tr[position()>1]')
        for row in rows:
            price = row.xpath('./td[3]/text()').get()
            dd = {
                'brand': self.brand,
                'cat_no': response.meta.get('cat_no'),
                'package': strip(row.xpath('./td[1]/text()').get()),
                'cost': price and first(first(p.findall(price), None), None),
                'stock_num': strip(row.xpath('./td[4]/text()').get()),
                'currency': 'GBP',
            }
            yield ProductPackage(**dd)
