from urllib.parse import urljoin

import scrapy

from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation
from product_spider.utils.spider_mixin import BaseSpider


class EuropaSpider(BaseSpider):
    name = "europa"
    allow_domain = ["crm.jrc.ec.europa.eu/"]
    start_urls = ["https://crm.jrc.ec.europa.eu/", ]

    base_url = "https://crm.jrc.ec.europa.eu"

    def parse(self, response, **kwargs):
        rows = response.xpath("//ul[@id='submenu']//ul/li")
        for row in rows:
            url = urljoin(self.base_url, row.xpath(".//a/@href").get())
            yield scrapy.Request(
                url=url,
                callback=self.parse_list
            )

    def parse_list(self, response):
        """解析列表页"""
        cat_no = response.xpath("//li[@class=' zebra']//b[@class='brand']/text()").get()
        price = response.xpath("//span[@class='prod-lijst-prijs  ']/text()").get()
        meta = {
            "cat_no": cat_no,
            "price": price,
        }
        rows = response.xpath("//ul[@class='productlijst-klein']//a")
        for row in rows:
            if row:
                url = urljoin(self.base_url, row.xpath(".//@href").get())  # 详情页
                yield scrapy.Request(
                    url=url,
                    callback=self.parse_detail,
                    meta=meta
                )

        next_url = urljoin(self.base_url,
                           response.xpath("//div[@class='center']//a[contains(text(), 'next »')]/@href").get())
        if next_url and next_url != self.base_url:
            yield scrapy.Request(
                url=next_url,
                callback=self.parse
            )

    def parse_detail(self, response):
        """解析详情页"""
        cat_no = response.meta["cat_no"]
        price = response.meta["price"]
        package = response.xpath("//tr[@class='netmass odd']//td[last()]/text()").get()
        parent = response.xpath("//div[@class='second']//a[last()-1]/text()").get()
        info2 = response.xpath("//tr[@class='storagetemperature even']//td[last()]/text()").get()

        en_name = response.xpath("//div[@id='content-midden']//h1/text()").get()

        d = {
            "cat_no": cat_no,
            "brand": self.name,
            "parent": parent,
            "en_name": en_name,
            "prd_url": response.url,
            "info2": info2,
        }

        dd = {
            "brand": self.name,
            "cat_no": cat_no,
            "cost": price,
            "package": package,
            "currency": "EUR"
        }

        ddd = {
            "platform": self.name,
            "vendor": self.name,
            "brand": self.name,
            "source_id": f'{self.name}_{d["cat_no"]}_{dd["package"]}',
            "parent": d["parent"],
            "en_name": d["en_name"],
            'cat_no': d["cat_no"],
            'package': dd['package'],
            'cost': dd['cost'],
            "currency": dd["currency"],
            "prd_url": d["prd_url"],
        }

        dddd = {
            "platform": self.name,
            "vendor": self.name,
            "brand": self.name,
            "source_id":  f'{self.name}_{d["cat_no"]}',
            'cat_no': d["cat_no"],
            'package': dd['package'],
            'discount_price': dd['cost'],
            'price': dd['cost'],
            'currency': dd["currency"],
        }

        yield RawData(**d)
        yield ProductPackage(**dd)
        yield SupplierProduct(**ddd)
        yield RawSupplierQuotation(**dddd)
