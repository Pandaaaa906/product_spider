import json

from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation
import scrapy

from product_spider.utils.cost import parse_cost
from product_spider.utils.items_translate import rawdata_to_supplier_product, product_package_to_raw_supplier_quotation
from product_spider.utils.spider_mixin import BaseSpider


class A2bchemSpider(BaseSpider):
    name = "a2bchem"
    allow_domain = ["a2bchem.com"]
    start_urls = ["https://www.a2bchem.com/Pharmaceutical-Intermediates.html", ]

    def parse(self, response, **kwargs):
        rows = response.xpath("//table[@class='q_table']/tbody/tr")
        for row in rows:
            url = row.xpath(".//td[7]//a/@href").get()
            yield scrapy.Request(
                url=url,
                callback=self.parse_detail
            )
        next_url = response.xpath("//li[@class='page-item']//a[@rel='next']/@href").get()
        if next_url:
            yield scrapy.Request(
                url=next_url,
                callback=self.parse
            )

    def parse_detail(self, response):
        cat_no = response.xpath("//td[contains(text(), 'Catalog Number:')]/following-sibling::td/text()").get()
        mdl = response.xpath("//td[contains(text(), 'MDL Number:')]/following-sibling::td/text()").get()
        inchl = response.xpath("//td[contains(text(), 'InChl:')]/following-sibling::td/text()").get()
        inchl_key = response.xpath("//td[contains(text(), 'InChl Key:')]/following-sibling::td/text()").get()
        iupac = response.xpath("//td[contains(text(), 'IUPAC Name:')]/following-sibling::td/text()").get()

        prd_attrs = json.dumps({
            "inchl": inchl,
            "inchl_key": inchl_key,
            "iupac": iupac,
        })

        d = {
            "brand": self.name,
            "parent": response.xpath("//div[@class='crumbs']//a[last()]/text()").get(),
            "cat_no": cat_no,
            "en_name": response.xpath("//td[contains(text(), 'Chemical Name:')]/following-sibling::td/text()").get(),
            "cas": response.xpath("//td[contains(text(), 'CAS Number:')]/following-sibling::td/text()").get(),
            "smiles": response.xpath("//td[contains(text(), 'SMILES:')]/following-sibling::td/text()").get(),
            "mf": response.xpath("//td[contains(text(), 'Molecular Formula:')]/following-sibling::td/text()").get(),
            "mw": response.xpath("//td[contains(text(), 'Molecular Weight:')]/following-sibling::td/text()").get(),
            "prd_url": response.url,
            "img_url": response.xpath("//div[@class='pd_f1']/img/@src").get(),
            "info1": response.xpath("//td[contains(text(), 'IUPAC Name:')]/following-sibling::td/text()").get(),
            "mdl": mdl,
            "attrs": prd_attrs,
        }
        yield RawData(**d)
        ddd = rawdata_to_supplier_product(d, platform=self.name, vendor=self.name)
        yield SupplierProduct(**ddd)

        rows = response.xpath("//table[@class='q_table']/tbody/tr")
        for row in rows:
            original_price = row.xpath(".//td[4]/text()").get()
            price = row.xpath(".//td[5]/text()").get('')
            stock_info = row.xpath(".//td[3]/text()").get()
            dd = {
                "brand": self.name,
                "cat_no": cat_no,
                "package": row.xpath(".//td[1]/text()").get(),
                "cost": parse_cost(price),
                "price": parse_cost(original_price),
                "currency": 'USD',
                "delivery_time": stock_info,
            }
            yield ProductPackage(**dd)

            dddd = product_package_to_raw_supplier_quotation(d, dd, platform=self.name, vendor=self.name)
            yield RawSupplierQuotation(**dddd)
