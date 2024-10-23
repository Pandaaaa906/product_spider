from urllib.parse import urljoin
import json
from scrapy import Request
import re
from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation
from product_spider.utils.items_translate import rawdata_to_supplier_product, product_package_to_raw_supplier_quotation
from product_spider.utils.spider_mixin import BaseSpider


class BPSpider(BaseSpider):
    name = "bp"
    start_urls = ["https://www.pharmacopoeia.com/shop/products", ]
    base_url = "https://www.pharmacopoeia.com/"

    def parse(self, response, **kwargs):
        rel_urls = response.xpath('//ul[@class="spl-list"]//div/a/@href').getall()
        for rel_url in rel_urls:
            yield Request(urljoin(response.url, rel_url), callback=self.parse_detail)

        next_page = response.xpath('//div[@class="pagination"]//li[@class="selected"]/following-sibling::li/a/@href') \
            .get()
        if next_page:
            yield Request(urljoin(response.url, next_page), callback=self.parse)

    def parse_detail(self, response):
        tmp = '//div[@class="col spd-col" and contains(text(), {!r})]/following-sibling::div//text()'
        cat_no = response.xpath(tmp.format('Catalogue number')).get()
        batch_num = response.xpath(tmp.format('Batch number')).get()  # 批号
        shipping_info = response.xpath(tmp.format('Shipping conditions')).get()  # 运输条件
        controlled_drug = response.xpath(tmp.format('Controlled drug')).get()  # 管控产品
        expiry_date = response.xpath(tmp.format('Expiry date')).get()  # 有效期

        attrs = json.dumps({
            'controlled_drug': controlled_drug,
        })

        package_attrs = json.dumps({
            'batch_num': batch_num,
            'expiry_date': expiry_date,
        })

        package = response.xpath(tmp.format('Pack size')).get()
        if package:
            package = package.replace(' ', '')
        cost = response.xpath(tmp.format('Price')).get()
        if cost:
            cost = re.search(r'(?<=£)\d+', cost).group()

        d = {
            'brand': self.name,
            'cat_no': cat_no,
            'en_name': ''.join(response.xpath('//h1//text()').getall()),
            "cas": response.xpath(tmp.format('CAS number')).get(),
            "info2": ''.join(response.xpath(tmp.format('Long term storage conditions')).getall()),
            "stock_info": response.xpath(tmp.format('Availability')).get(),
            "prd_url": response.url,
            "shipping_info": shipping_info,
            "attrs": attrs
        }

        dd = {
            "brand": self.name,
            "cat_no": cat_no,
            "package": package,
            "cost": cost,
            "currency": "GBP",
            "attrs": package_attrs,
        }

        ddd = rawdata_to_supplier_product(d, platform=self.name, vendor=self.name)
        dddd = product_package_to_raw_supplier_quotation(d, dd, platform=self.name, vendor=self.name)

        yield RawData(**d)
        yield ProductPackage(**dd)
        yield SupplierProduct(**ddd)
        yield RawSupplierQuotation(**dddd)
