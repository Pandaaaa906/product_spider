from urllib.parse import urljoin

import scrapy

from product_spider.items import RawData, ProductPackage, SupplierProduct
from product_spider.utils.cost import parse_cost
from product_spider.utils.spider_mixin import BaseSpider


class BritiscientificSpider(BaseSpider):
    name = "britiscientific"
    start_urls = ["https://britiscientific.com/product", ]
    base_url = "https://britiscientific.com"

    def parse(self, response, **kwargs):
        urls = response.xpath(
            '//h4[contains(text(), "Our Products")]/following-sibling::div//i/following-sibling::a/@href'
        ).getall()
        for url in urls:
            yield scrapy.Request(
                url=url,
                callback=self.parse_list
            )

    def parse_list(self, response):
        urls = response.xpath("//tbody[@class='category-body']//td/a/@href").getall()
        for url in urls:
            url = urljoin(self.base_url, url)
            yield scrapy.Request(
                url=url,
                callback=self.parse_detail
            )

    def parse_detail(self, response):
        tmp_xpath = "//strong[contains(text(), {!r})]/parent::p/text()"
        parent = response.xpath("//ul[@class='breadcrumb']/li[last()-1]//text()").get()
        en_name = response.xpath("//h6[@class='font-weight-bold']/text()").get()
        cat_no = response.xpath(tmp_xpath.format("Product Code:")).get()
        cas = response.xpath(tmp_xpath.format("CAS No.:")).get()
        package = response.xpath("//table[@class='table table-bordered']/tbody//td[last()-1]/text()").get()
        cost = parse_cost(response.xpath("//table[@class='table table-bordered']/tbody//td[last()]/text()").get())

        d = {
            "brand": self.name,
            "parent": parent,
            "en_name": en_name,
            "cat_no": cat_no,
            "cas": cas,
            "prd_url": response.url
        }

        dd = {
            "brand": d["brand"],
            "cat_no": d["cat_no"],
            "package": package,
            "cost": cost,
            "currency": "INR",
        }

        ddd = {
            "platform": self.name,
            "vendor": self.name,
            "brand": self.name,
            "parent": d["parent"],
            "en_name": d["en_name"],
            "cas": d["cas"],
            'cat_no': d["cat_no"],
            'package': dd['package'],
            'cost': dd['cost'],
            "currency": dd["currency"],
            "prd_url": d["prd_url"],
        }

        yield RawData(**d)
        yield ProductPackage(**dd)
        yield SupplierProduct(**ddd)
