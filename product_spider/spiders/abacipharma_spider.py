import json
from urllib.parse import urljoin

import scrapy

from product_spider.utils.functions import strip
from product_spider.utils.items_translate import rawdata_to_supplier_product, product_package_to_raw_supplier_quotation
from product_spider.utils.spider_mixin import BaseSpider
from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation


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

        next_url = urljoin(
            response.url, response.xpath("//li[@class='next-page']/a[contains(text(), Next)]/@href").get()
        )
        if next_url:
            yield scrapy.Request(
                url=next_url,
                callback=self.parse
            )

    def parse_detail(self, response):
        parent = response.xpath("//div[@class='breadcrumb']//li[last()-1]//span[@itemprop='title']/text()").get()
        cat_no = response.xpath(
            "//div[@class='short-description']//strong[contains(text(), 'Catalog:')]/following-sibling::span/text()").get()
        delivery_time = response.xpath("//*[contains(text(), 'Delivery date:')]/following-sibling::span/text()").get()
        inchl_key = response.xpath("//b[contains(text(), 'INCHIKEY:  ')]/parent::td/following-sibling::td/text()").get()

        prd_attrs = json.dumps({
            "inchl_key": inchl_key
        })

        d = {
            "brand": self.name,
            "parent": parent,
            "cat_no": cat_no,
            "en_name": strip(response.xpath("//h1[@itemprop='name']/text()").get()),
            "cas": response.xpath(
                "//div[@class='short-description']//strong[contains(text(), 'CAS:')]/following-sibling::span/text()").get(),
            "smiles": response.xpath(
                "//b[contains(text(), 'Smiles:  ')]/parent::td/following-sibling::td/text()").get(),
            "mf": response.xpath("//b[contains(text(), 'Formula:')]/parent::td/following-sibling::td/text()").get(),
            "mw": response.xpath("//b[contains(text(), 'Mol Weight: ')]/parent::td/following-sibling::td/text()").get(),
            "prd_url": response.url,
            "img_url": response.xpath("//div[@class='picture']//img/@src").get(),
            "attrs": prd_attrs,
        }
        yield RawData(**d)
        ddd = rawdata_to_supplier_product(d, platform=self.name, vendor=self.name)
        yield SupplierProduct(**ddd)

        rows = response.xpath("//ul[@class='option-list']//tr[position()>1]")
        for row in rows:
            purity = row.xpath(".//td[@class='attribute_purity']/span/text()").get()
            dd = {
                "brand": self.name,
                "cat_no": cat_no,
                "package": row.xpath(".//td[@class='attribute_name']/span/text()").get(),
                "cost": row.xpath(".//td[@class='attribute_price']/input/@value").get(),
                "delivery_time": delivery_time,
                "currency": "USD",
                "purity": purity
            }
            yield ProductPackage(**dd)

            dddd = product_package_to_raw_supplier_quotation(d, dd, platform=self.name, vendor=self.name)
            yield RawSupplierQuotation(**dddd)
