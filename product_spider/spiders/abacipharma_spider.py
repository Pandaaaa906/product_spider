from urllib.parse import urljoin

import scrapy
from product_spider.utils.spider_mixin import BaseSpider
from product_spider.items import RawData, ProductPackage


class AbacipharmaSpider(BaseSpider):
    name = "abacipharma"
    allow_domain = ["aaronchem.com"]
    start_urls = ["http://www.abacipharma.com/Standard%20Reference%20Material?orderby=0&pagesize=15&viewmode=list", ]

    def parse(self, response, **kwargs):
        urls = response.xpath("//div[@class='details']//a/@href").getall()
        for url in urls:
            url = urljoin(response.url, url)

            yield scrapy.Request(
                url=url,
                callback=self.parse_detail,
            )
        next_url = response.xpath("//li[@class='next-page']/a[contains(text(), Next)]/@href").get()
        next_url = urljoin(response.url, next_url)
        if next_url:
            yield scrapy.Request(
                url=next_url,
                callback=self.parse
            )

    def parse_detail(self, response):
        parent = response.xpath("//div[@class='breadcrumb']//li[last()]/strong[@class='current-item']/text()").get()
        cat_no = response.xpath(
            "//div[@class='short-description']//strong[contains(text(), 'Catalog:')]/following-sibling::span/text()").get()
        d = {
            "brand": self.name,
            "parent": parent,
            "cat_no": cat_no,
            "en_name": response.xpath("//h1[@itemprop='name']/text()").get(),
            "cas": response.xpath(
                "//div[@class='short-description']//strong[contains(text(), 'CAS:')]/following-sibling::span/text()").get(),
            "smiles": response.xpath(
                "//b[contains(text(), 'Smiles:  ')]/parent::td/following-sibling::td/text()").get(),
            "mf": response.xpath("//b[contains(text(), 'Formula:')]/parent::td/following-sibling::td/text()").get(),
            "mw": response.xpath("//b[contains(text(), 'Mol Weight: ')]/parent::td/following-sibling::td/text()").get(),
            "prd_url": response.url,
            "img_url": response.xpath("//div[@class='picture']//img/@src").get(),
        }
        yield RawData(**d)

        rows = response.xpath("//ul[@class='option-list']//tr[position()>1]")
        for row in rows:
            dd = {
                "brand": self.name,
                "cat_no": cat_no,
                "package": row.xpath(".//td[@class='attribute_name']/span/text()").get(),
                "cost": row.xpath(".//td[@class='attribute_price']/input/@value").get(),
                "currency": "USD",

            }

            yield ProductPackage(**dd)
