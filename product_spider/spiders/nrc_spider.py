from urllib.parse import urljoin

import scrapy

from product_spider.items import RawData, ProductPackage, SupplierProduct
from product_spider.utils.spider_mixin import BaseSpider


class NrcPrdSpider(BaseSpider):
    name = 'nrc'
    base_url = "https://shop-magasin.nrc-cnrc.gc.ca/"
    start_urls = ["https://shop-magasin.nrc-cnrc.gc.ca"]

    def parse(self, response, **kwargs):
        url = urljoin(self.base_url, response.xpath('//a[@name="p2"]/@href').get())
        yield scrapy.Request(
            url=url,
            callback=self.parse_list,
        )

    def parse_list(self, response):
        rows = response.xpath("//div[@class='cat-secnav-areaname']")
        for row in rows:
            url = urljoin(self.base_url, row.xpath("./a/@href").get())
            yield scrapy.Request(
                url=url,
                callback=self.parse_list_detail,
            )

    def parse_list_detail(self, response):
        parent = response.xpath("//h1[@id='wb-cont']/text()").get()
        rows = response.xpath("//div[@class = 'cat-prd-id']")
        for row in rows:
            cat_no = row.xpath("./text()").get('').strip()
            package = row.xpath("./parent::td//span/text()").get()
            img_url = row.xpath("./parent::td/preceding-sibling::td/img/@src").get()
            cost, currency = row.xpath("./parent::td/following-sibling::td//td[last()-1]/text()").get('').strip().split()
            d = {
                "brand": self.name,
                "parent": parent,
                "cat_no": cat_no,
                "img_url": img_url,
                "prd_url": response.url,
            }
            dd = {
                "brand": self.name,
                "cat_no": cat_no,
                "package": package,
                "cost": cost,
                "currency": currency,
            }

            ddd = {
                "platform": self.name,
                "vendor": self.name,
                "brand": self.name,
                "parent": d["parent"],
                'cat_no': d["cat_no"],
                'package': dd['package'],
                'cost': dd['cost'],
                "currency": dd["currency"],
                "img_url": d["img_url"],
                "prd_url": d["prd_url"],
            }
            if not d:
                return
            yield RawData(**d)
            yield ProductPackage(**dd)
            yield SupplierProduct(**ddd)

