import re
from datetime import datetime
from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData, ProductPackage
from product_spider.utils.spider_mixin import BaseSpider
from product_spider.utils.functions import strip, dumps
from product_spider.utils.cost import parse_cost


class SynthoseSpider(BaseSpider):
    name = "synthose"
    base_url = "https://synthose.com/"
    start_urls = ['https://synthose.com/products', ]

    def parse(self, response, **kwargs):
        rel_urls = response.xpath('//div[@class="product"]//h3/a/@href').getall()
        for rel_url in rel_urls:
            yield Request(urljoin(self.base_url, rel_url), callback=self.parse_detail)

        next_page = response.xpath('//a[contains(text(), "Next")]/@href').get()
        if next_page:
            yield Request(urljoin(response.url, next_page), callback=self.parse)

    def parse_detail(self, response):
        tmp = '//dt[contains(text(), {!r})]/following-sibling::dd//text()'
        img_url = response.xpath('//img[@class="img-thumbnail"]/@src').get()
        d = {
            'brand': self.name,
            'parent': ', '.join(response.xpath('//div[@role="navigation"]//a/text()').getall()),
            'cat_no': response.xpath('//p[contains(text(), "Catalogue Number:")]/span/text()').get(),
            'en_name': (response.xpath('//main[@id="product"]//header/h1/text()').get()),
            'mf': (response.xpath(tmp.format("Molecular Formula")).get()),
            'mw': (response.xpath(tmp.format("Molecular Weight")).get()),
            'cas': (response.xpath(tmp.format("CAS Number")).get()),
            'purity': (response.xpath(tmp.format("Chemical Purity")).get()),
            'appearance': (response.xpath(tmp.format("Appearance")).get()),
            'info1': ''.join(response.xpath('//main[@id="product"]//header/h1/following-sibling::p//text()').getall()),
            'info2': ''.join(response.xpath(tmp.format("Storage")).getall()),

            'stock_info': (response.xpath('//table[@class="stock"]//tr[1]/td[2]/text()').get()),
            'img_url': img_url and urljoin(self.base_url, img_url),
            'prd_url': response.url,
        }
        yield RawData(**d)

        today = datetime.now().date()
        rows = response.xpath('//table[contains(@class, "prices")]/tbody/tr')
        for row in rows:
            availability = strip(row.xpath('./td[3]/span/text()').get(''))
            stock_d = {}
            delivery_time = None
            if availability:
                stock_d = (m := re.search(r'≥?(?P<stock_num>\d+)\s*ship\s*(?P<delivery_date>.+)', availability, re.MULTILINE)) and m.groupdict()
            if dt := stock_d.get('delivery_date'):
                try:
                    delivery_date = datetime.strptime(dt, '%b %d, %Y')
                    delivery_time = (delivery_date.date() - today).days
                except Exception as e:
                    self.logger.warning(e)
            dd = {
                "brand": self.name,
                "cat_no": d["cat_no"],
                "package": row.xpath('./td[1]/text()').get(),
                "cost": parse_cost(row.xpath('./td[2]/text()').get()),
                "price": parse_cost(row.xpath('./td[2]/text()').get()),
                "currency": "USD",
                "stock_num": stock_d.get("stock_num"),
                "delivery_time": delivery_time,
                "attrs": dumps({"availability": availability})
            }
            yield ProductPackage(**dd)
