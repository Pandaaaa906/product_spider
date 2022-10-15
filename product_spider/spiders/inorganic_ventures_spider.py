import scrapy
from lxml import etree
from more_itertools import first

from product_spider.items import RawData, ProductPackage, SupplierProduct
from product_spider.utils.cost import parse_cost
from product_spider.utils.spider_mixin import BaseSpider


class InorganicVentureSpider(BaseSpider):
    name = "inorganicventure"
    start_urls = ["https://www.inorganicventures.com/products"]
    base_url = "www.inorganicventures.com"

    def parse(self, response, **kwargs):
        rows = response.xpath("//li[@class='item product product-item']")
        for row in rows:
            prd_id = row.xpath(".//input[@name='product']/@value").get()
            if not prd_id:
                continue
            yield scrapy.FormRequest(
                url="https://www.inorganicventures.com/productinfo.php",
                formdata={"productId": prd_id},
                callback=self.parse_detail,
            )

        next_url = response.xpath("//span[contains(text(), 'Next Page')]/parent::a/@href").get()
        if next_url:
            yield scrapy.Request(
                url=next_url,
                callback=self.parse,
            )

    def parse_detail(self, response):
        html = etree.HTML(response.text)
        img_url = first(html.xpath("//div[@class='col-md-4 text-center']/img/@src"))
        cost = parse_cost(first(html.xpath("//span[@class='price']/text()")))

        raw_cat_no = first(html.xpath("//h4[contains(text(), 'Part #:')]/parent::div/following-sibling::div/p/text()"),
                           None)
        if not raw_cat_no:
            return
        raw_package, cat_no = raw_cat_no[::-1].split("-", 1)

        cat_no = cat_no[::-1]
        package = raw_package[::-1]

        d = {
            "brand": self.name,
            "cat_no": cat_no,
            "img_url": img_url,
            "prd_url": response.url,
        }
        dd = {
            "brand": self.name,
            "cat_no": cat_no,
            "package": package,
            "cost": cost,
            "currency": "USD",
        }

        ddd = {
            "platform": self.name,
            "vendor": self.name,
            "brand": self.name,
            'cat_no': d["cat_no"],
            'package': dd['package'],
            'cost': dd['cost'],
            "currency": dd["currency"],
            "img_url": d["img_url"],
            "prd_url": d["prd_url"],
        }
        yield RawData(**d)
        yield ProductPackage(**dd)
        yield SupplierProduct(**ddd)
