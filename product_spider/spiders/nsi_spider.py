import scrapy

from product_spider.items import RawData, ProductPackage, SupplierProduct
from product_spider.utils.spider_mixin import BaseSpider


class NSISpider(BaseSpider):
    """nsi"""
    name = "nsi"
    start_urls = ["https://www.nsilabsolutions.com/product-category/environmental/"]
    base_url = "https://www.nsilabsolutions.com/"

    def parse(self, response, **kwargs):
        urls = response.xpath('//ul[@class="product_cats submenu"]//li/a/@href').getall()
        for url in urls:
            yield scrapy.Request(
                url=url,
                callback=self.parse_list,
            )

    def parse_list(self, response):
        urls = response.xpath("//div[@class='prod-litems section-list']//h3/a//@href").getall()
        for url in urls:
            yield scrapy.Request(
                url=url,
                callback=self.parse_detail,
            )
        next_url = response.xpath("//ul[@class='page-numbers']/li[last()]/a/@href").get()
        if next_url:
            yield scrapy.Request(
                url=next_url,
                callback=self.parse_list,
            )

    def parse_detail(self, response):
        parent = response.xpath("//ul[@class='b-crumbs']/li[last()-1]/a/text()").get()
        en_name = response.xpath("//ul[@class='b-crumbs']/li[last()]/text()").get()
        cat_no = response.xpath("//dd[@class='sku_wrapper']//text()").get()
        img_url = response.xpath("//a[@class='fancy-img']/img/@src").get()
        cost = response.xpath("//p[@class='prod-price']/span[@class='woocommerce-Price-amount amount']/text()").get()
        d = {
            "brand": self.name,
            "parent": parent,
            "en_name": en_name,
            "cat_no": cat_no,
            "img_url": img_url,
            "prd_url": response.url,
        }
        dd = {
            "brand": self.name,
            "cat_no": cat_no,
            "package": "1瓶",
            "cost": cost,
            "currency": "USD",
        }
        ddd = {
            "platform": self.name,
            "vendor": self.name,
            "brand": self.name,
            'cat_no': d["cat_no"],
            "parent": d["parent"],
            "en_name": d["en_name"],
            'package': dd['package'],
            'cost': dd['cost'],
            "currency": dd["currency"],
            "img_url": d["img_url"],
            "prd_url": d["prd_url"],
        }

        yield RawData(**d)
        yield ProductPackage(**dd)
        yield SupplierProduct(**ddd)
