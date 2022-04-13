import json
from urllib.parse import urljoin

import scrapy

from product_spider.items import RawData, ProductPackage
from product_spider.utils.spider_mixin import BaseSpider


class NibscPrdSpider(BaseSpider):
    name = 'nibsc'
    base_url = "https://www.nibsc.org/"
    start_urls = ["https://www.nibsc.org/products.aspx", ]

    def parse(self, response, **kwargs):
        rows = response.xpath("//*[@class='products-sidebar']//li")
        for row in rows:
            url = urljoin(self.base_url, row.xpath("./ul//a/@href").get())
            yield scrapy.Request(
                url=url,
                callback=self.parse_list
            )

    def parse_list(self, response):
        rows = response.xpath("//*[contains(text(), 'Product details')]")
        for row in rows:
            url = urljoin(self.base_url, row.xpath("./@href").get())
            yield scrapy.Request(
                url=url,
                callback=self.parse_detail,
            )

    def parse_detail(self, response):
        en_name = response.xpath("//*[@class='col-12']/h1/text()").get()
        cat_no = response.xpath(
            "//*[contains(text(), 'Product number')]//parent::div/following-sibling::div/p/text()").get()
        parent = ','.join(response.xpath(
            "//div[@class='col-12 col-md-7 mb-5 mb-md-3']//*[contains(text(), 'Category')]/parent::div/following-sibling::div//li/a/text()"
        ).getall())
        prd_info = response.xpath(
            "//*[contains(text(), 'Product description')]/parent::div/following-sibling::div/p/text()").get()  # 产品其他信息

        cost = response.xpath("//*[contains(text(), 'Unit price')]/parent::div/following-sibling::div/p/text()").get()
        if cost is not None:
            cost = cost.replace("£", '')

        coa_url = urljoin(
            self.base_url,
            response.xpath(
                "//*[contains(text(), 'Instructions for Use')]/parent::div/following-sibling::div/a/@href").get()
        )
        prd_attrs = json.dumps({
            "product_info": prd_info
        })

        package_attrs = json.dumps({
            "coa_url": coa_url
        })

        d = {
            "brand": self.name,
            "cat_no": cat_no,
            "parent": parent,
            "en_name": en_name,
            "prd_url": response.url,
            "attrs": prd_attrs,
        }

        dd = {
            "brand": self.name,
            "cat_no": cat_no,
            "package": "vial",
            "cost": cost,
            "currency": "GBP",
            "attrs": package_attrs,
        }
        yield RawData(**d)
        yield ProductPackage(**dd)
