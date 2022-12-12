from scrapy import Request
from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation
from product_spider.utils.cost import parse_cost
from product_spider.utils.spider_mixin import BaseSpider
import re

class AcintsSpider(BaseSpider):
    name = "acints"
    allowed_domains = ["acints.com"]
    start_urls = ["https://www.acints.com/products", ]

    def parse(self, response, **kwargs):
        urls = response.xpath("//ul[@class='productList']//p[position()>1]/a/@href").getall()
        for url in urls:
            if url:
                yield Request(
                    url=url,
                    callback=self.parse_detail
                )
        next_url = response.xpath("//div[@class='middle']//p[last()]//a[last()-1]/@href").get()

        if next_url:
            yield Request(
                next_url,
                callback=self.parse
            )

    def parse_detail(self, response):
        cat_no = response.xpath("//div[@id='primary']//span[contains(text(), 'Product Code:')]//parent::p/text()").get()

        d = {
            "brand": self.name,
            "en_name": response.xpath("//div[@id='primary']/h1/text()").get(),
            "cat_no": cat_no,
            "cas": response.xpath("//div[@id='primary']//span[contains(text(), 'CAS No:')]//parent::p/text()").get(),
            "mf": response.xpath(
                "//span[@class='pParam'][contains(text(), 'Molecular Formula:')]/parent::p/text()").get(),
            "mw": response.xpath(
                "//div[@id='primary']//span[contains(text(), 'Molecular Weight:')]//parent::p/text()").get(),
            "purity": response.xpath("//div[@id='primary']//span[contains(text(), 'Purity:')]//parent::p/text()").get(),
            "prd_url": response.url,
            "img_url": response.xpath("//div[@class='productImg']//img/@src").get(),
            "mdl": response.xpath("//div[@id='primary']//span[contains(text(), 'MDL No:')]//parent::p/text()").get()
        }

        yield RawData(**d)

        rows = response.xpath("//form[@class='cartform ajaxform']//p/label")
        for row in rows:
            price = row.xpath('.//span[@class="baseprice"]/text()').get()
            package = re.search(
                r'(?<=per ).*(?=:)', row.xpath(".//span[@class='pParam']/text()").get()
            )
            if not package:
                continue
            package = package.group()

            dd = {
                "brand": self.name,
                "cat_no": cat_no,
                "package": package,
                "cost": parse_cost(price),
                "currency": "GBP"  # Great Britain Pound
            }
            yield ProductPackage(**dd)

            ddd = {
                "platform": self.name,
                "vendor": self.name,
                "brand": self.name,
                "source_id": f'{self.name}_{d["cat_no"]}_{dd["package"]}',
                "en_name": d["en_name"],
                "cas": d["cas"],
                "mf": d["mf"],
                "mw": d["mw"],
                "purity": d["purity"],
                'cat_no': d["cat_no"],
                'package': dd['package'],
                'cost': dd['cost'],
                "currency": dd["currency"],
                "img_url": d["img_url"],
                "prd_url": response.url,
            }
            dddd = {
                "platform": self.name,
                "vendor": self.name,
                "brand": self.name,
                "source_id": f'{self.name}_{d["cat_no"]}',
                'cat_no': d["cat_no"],
                'package': dd['package'],
                'discount_price': dd['cost'],
                'price': dd['cost'],
                'cas': d["cas"],
                'currency': dd["currency"],
            }
            yield SupplierProduct(**ddd)
            yield RawSupplierQuotation(**dddd)
